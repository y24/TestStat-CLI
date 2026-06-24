from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud.bug import (
    get_bug_chart_metadata,
    get_bug_cumulative,
)
from app.models.plan import Plan, PlanDaily, PlanLabel
from app.models.progress import DailyProgress, FileProgress, TestResultBugSnapshot, Testing
from app.models.project import Project
from app.schemas.pb_chart import (
    PastPlanSeries,
    PastPlanSeriesItem,
    PbChartRange,
    PbChartResponse,
    PbChartSeriesItem,
)


# ---------- helpers ----------

def _label_filter(label: str | None):
    return Plan.label.is_(None) if label is None else Plan.label == label


def _get_disabled_labels(db: Session, testing_id: int) -> set[str]:
    return set(
        db.scalars(
            select(PlanLabel.label).where(
                PlanLabel.testing_id == testing_id,
                PlanLabel.is_disabled.is_(True),
            )
        )
    )


def _label_is_disabled(db: Session, testing_id: int, label: str | None) -> bool:
    if label is None:
        return False
    return db.scalar(
        select(PlanLabel.id).where(
            PlanLabel.testing_id == testing_id,
            PlanLabel.label == label,
            PlanLabel.is_disabled.is_(True),
        )
    ) is not None


def _date_range(start: date, end: date) -> list[date]:
    result = []
    d = start
    while d <= end:
        result.append(d)
        d += timedelta(days=1)
    return result


# ---------- データ取得 ----------

def _get_active_plans(db: Session, testing_id: int, label: str | None) -> list[Plan]:
    """有効な計画を取得。label=None の場合は無効 label を除いた全 label の有効計画を返す。"""
    if _label_is_disabled(db, testing_id, label):
        return []
    q = select(Plan).where(Plan.testing_id == testing_id, Plan.is_active.is_(True))
    if label is not None:
        q = q.where(Plan.label == label)
    plans = list(db.scalars(q))
    if label is None:
        disabled_labels = _get_disabled_labels(db, testing_id)
        plans = [plan for plan in plans if plan.label not in disabled_labels]
    return plans


def _get_plan_daily_map(db: Session, plan_ids: list[int]) -> dict[date, int]:
    """日付ごとの計画消化数合計 {date: sum(planned_count)}"""
    if not plan_ids:
        return {}
    rows = db.execute(
        select(PlanDaily.date, func.sum(PlanDaily.planned_count))
        .where(PlanDaily.plan_id.in_(plan_ids))
        .group_by(PlanDaily.date)
    ).all()
    return {r[0]: r[1] for r in rows}


def _get_actual_daily_map(db: Session, testing_id: int, label: str | None) -> dict[date, int]:
    """日付ごとの実績消化数合計 {date: sum(executed)}"""
    if _label_is_disabled(db, testing_id, label):
        return {}
    q = select(DailyProgress.date, func.sum(DailyProgress.executed)).where(
        DailyProgress.testing_id == testing_id
    )
    if label is not None:
        q = q.where(DailyProgress.label == label)
    else:
        disabled_labels = _get_disabled_labels(db, testing_id)
        if disabled_labels:
            q = q.where((DailyProgress.label.is_(None)) | (DailyProgress.label.not_in(disabled_labels)))
    rows = db.execute(q.group_by(DailyProgress.date)).all()
    return {r[0]: r[1] for r in rows}


def _get_test_result_bug_daily_map(
    db: Session, testing_id: int, label: str | None = None
) -> dict[date, tuple[int, int, int]]:
    """日付ごとのテスト結果由来の (検出増分, 見送り件数, 完了件数) スナップショットを返す。

    label 指定時はそのテスト種別のみ。label=None（全て）は全 label を日付ごとに合算する。
    """
    if _label_is_disabled(db, testing_id, label):
        return {}
    q = select(
        TestResultBugSnapshot.snapshot_date,
        func.sum(TestResultBugSnapshot.detected_count),
        func.sum(TestResultBugSnapshot.suspend_count),
        func.sum(TestResultBugSnapshot.fixed_count),
    ).where(TestResultBugSnapshot.testing_id == testing_id)
    if label is not None:
        q = q.where(TestResultBugSnapshot.label == label)
    else:
        disabled_labels = _get_disabled_labels(db, testing_id)
        if disabled_labels:
            q = q.where((TestResultBugSnapshot.label.is_(None)) | (TestResultBugSnapshot.label.not_in(disabled_labels)))
    rows = db.execute(
        q.group_by(TestResultBugSnapshot.snapshot_date).order_by(TestResultBugSnapshot.snapshot_date)
    ).all()
    return {row[0]: (int(row[1]), int(row[2]), int(row[3])) for row in rows}


def _get_test_result_bug_metadata(db: Session, testing_id: int) -> tuple[bool, datetime | None]:
    q = select(
        func.count(TestResultBugSnapshot.id),
        func.max(TestResultBugSnapshot.sent_at),
    ).where(TestResultBugSnapshot.testing_id == testing_id)
    disabled_labels = _get_disabled_labels(db, testing_id)
    if disabled_labels:
        q = q.where((TestResultBugSnapshot.label.is_(None)) | (TestResultBugSnapshot.label.not_in(disabled_labels)))
    count, updated_at = db.execute(q).one()
    return (count or 0) > 0, updated_at


def _get_actual_metadata(db: Session, testing_id: int, label: str | None) -> tuple[int, datetime | None]:
    """実績の対象件数合計と更新日時。実績なし=0。"""
    if _label_is_disabled(db, testing_id, label):
        updated_at = db.scalar(select(Testing.updated_at).where(Testing.testing_id == testing_id))
        return 0, updated_at
    available_query = select(func.coalesce(func.sum(FileProgress.available_cases), 0)).where(
        FileProgress.testing_id == testing_id
    )
    if label is not None:
        available_query = available_query.where(FileProgress.label == label)
    else:
        disabled_labels = _get_disabled_labels(db, testing_id)
        if disabled_labels:
            available_query = available_query.where((FileProgress.label.is_(None)) | (FileProgress.label.not_in(disabled_labels)))

    available_cases, updated_at = db.execute(
        select(
            available_query.scalar_subquery(),
            select(Testing.updated_at)
            .where(Testing.testing_id == testing_id)
            .scalar_subquery(),
        )
    ).one()
    return available_cases or 0, updated_at


def _get_actual_labels(db: Session, testing_id: int, label: str | None) -> set[str | None]:
    """実績データが存在する label の集合。FileProgress がない計画 label の判定に使う。"""
    if _label_is_disabled(db, testing_id, label):
        return set()
    q = select(FileProgress.label).where(FileProgress.testing_id == testing_id).distinct()
    if label is not None:
        q = q.where(FileProgress.label == label)
    else:
        disabled_labels = _get_disabled_labels(db, testing_id)
        if disabled_labels:
            q = q.where((FileProgress.label.is_(None)) | (FileProgress.label.not_in(disabled_labels)))
    return set(db.scalars(q))


def _compute_plan_only_available_cases(plans: list[Plan], actual_labels: set[str | None]) -> int:
    """実績データがまだない計画の件数を、未実施扱いで実績母数へ補完する。"""
    return sum(plan.planned_total_cases for plan in plans if plan.label not in actual_labels)


# ---------- 系列計算 ----------

def _compute_plan_series(
    plans: list[Plan],
    plan_daily_map: dict[date, int],
    plan_start: date,
    plan_end: date,
    planned_total: int,
) -> tuple[dict[date, int], dict[date, int]]:
    """
    計画系列を計算。
    戻り値: (planned_remaining_map, planned_daily_map)
    planned_remaining_map: {date: remaining} — plan_start〜plan_end の全日
    planned_daily_map: {date: count} — 同上（エントリなし日は 0）
    """
    dates = _date_range(plan_start, plan_end)
    cumsum = 0
    remaining_map: dict[date, int] = {}
    daily_map: dict[date, int] = {}
    for d in dates:
        cnt = plan_daily_map.get(d, 0)
        cumsum += cnt
        daily_map[d] = cnt
        remaining_map[d] = planned_total - cumsum
    return remaining_map, daily_map


def _compute_actual_series(
    actual_daily_map: dict[date, int],
    available_cases: int,
) -> dict[date, int]:
    """
    実績系列（actual_remaining）を計算。
    日付間のギャップは前の値を引き継ぐ（CLI が実行されなかった日）。
    戻り値: {date: remaining} — actual_daily_map に含まれる日付のみ
    """
    if not actual_daily_map or available_cases == 0:
        return {}
    cumsum = 0
    remaining_map: dict[date, int] = {}
    for d in sorted(actual_daily_map):
        cumsum += actual_daily_map[d]
        remaining_map[d] = available_cases - cumsum
    return remaining_map


def _compute_test_result_bug_series(
    date_range: list[date],
    daily_map: dict[date, tuple[int, int, int]],
) -> dict[date, tuple[int, int, int]]:
    """テスト結果由来の不具合バーンダウン系列を date_range に補完する。

    daily_map は日付ごとの (検出増分, 見送り件数, 完了件数)。Azure DevOps と同じ考え方で、
    各日について 未解消(open) = 検出累積 − 見送り累積 − 完了累積 を算出する。
    一度検出した不具合（検出累積）は減らないが、完了・見送りが増えると未解消は減る。
    戻り値: {date: (open, suspended, resolved)}。データがない日は直前の累積を引き継ぐ。
    """
    result: dict[date, tuple[int, int, int]] = {}
    cum_detected = cum_suspended = cum_resolved = 0
    for d in date_range:
        if d in daily_map:
            detected, suspended, resolved = daily_map[d]
            cum_detected += detected
            cum_suspended += suspended
            cum_resolved += resolved
        open_count = max(cum_detected - cum_suspended - cum_resolved, 0)
        result[d] = (open_count, cum_suspended, cum_resolved)
    return result


def _build_series(
    date_range: list[date],
    plan_remaining: dict[date, int],
    plan_daily: dict[date, int],
    actual_remaining_sparse: dict[date, int],
    actual_daily: dict[date, int],
    bug_cumulative: dict[date, tuple[int, int, int]] | None = None,
) -> list[PbChartSeriesItem]:
    """
    全日付に対して系列エントリを生成。
    actual_remaining は実績データ日のみ持つ sparse dict → 前の値を引き継いで補完。
    bug_cumulative は {date: (open, suspended, resolved)}。None のときは不具合系列を None で埋める。
    """
    last_actual_remaining: int | None = None
    last_actual_date: date | None = max(actual_remaining_sparse) if actual_remaining_sparse else None
    items: list[PbChartSeriesItem] = []

    for d in date_range:
        # 計画
        pr = plan_remaining.get(d)
        pd = plan_daily.get(d)

        # 実績（実績データがある日は更新、ない日は前の値を引き継ぐ）
        if d in actual_remaining_sparse:
            last_actual_remaining = actual_remaining_sparse[d]
        ar: int | None = last_actual_remaining
        # 実績の最終データ日より後は None（将来は不明）
        if last_actual_date is not None and d > last_actual_date:
            ar = None

        ad: int | None = actual_daily.get(d)

        bug_open = bug_suspended = bug_resolved = None
        if bug_cumulative is not None:
            bug_open, bug_suspended, bug_resolved = bug_cumulative.get(d, (0, 0, 0))

        items.append(PbChartSeriesItem(
            date=d,
            planned_remaining=pr,
            actual_remaining=ar,
            planned_completed_daily=pd,
            actual_completed_daily=ad,
            bug_open=bug_open,
            bug_suspended=bug_suspended,
            bug_resolved=bug_resolved,
        ))
    return items


# ---------- 過去計画 ----------

def _compute_past_plans(
    db: Session,
    testing_id: int,
    label: str | None,
) -> list[PastPlanSeries]:
    """is_active=False の計画バージョンを系列化。"""
    if _label_is_disabled(db, testing_id, label):
        return []
    q = select(Plan).where(Plan.testing_id == testing_id, Plan.is_active.is_(False))
    if label is not None:
        q = q.where(Plan.label == label)
    past_plans = list(db.scalars(q.order_by(Plan.label.nullsfirst(), Plan.version.desc())))
    if label is None:
        disabled_labels = _get_disabled_labels(db, testing_id)
        past_plans = [plan for plan in past_plans if plan.label not in disabled_labels]
    if not past_plans:
        return []

    active_plans = _get_active_plans(db, testing_id, None) if label is None else []
    active_plans_by_label = {p.label: p for p in active_plans}

    all_ids = list({p.id for p in [*past_plans, *active_plans]})
    daily_rows = db.execute(
        select(PlanDaily.plan_id, PlanDaily.date, PlanDaily.planned_count)
        .where(PlanDaily.plan_id.in_(all_ids))
        .order_by(PlanDaily.date)
    ).all()

    # plan_id ごとにグループ化
    daily_by_plan: dict[int, dict[date, int]] = defaultdict(dict)
    for row in daily_rows:
        daily_by_plan[row[0]][row[1]] = row[2]

    result: list[PastPlanSeries] = []
    if label is None:
        plans_by_version: dict[int, list[Plan]] = defaultdict(list)
        for plan in past_plans:
            plans_by_version[plan.version].append(plan)

        for version in sorted(plans_by_version, reverse=True):
            version_past_plans = plans_by_version[version]
            past_labels = {p.label for p in version_past_plans}
            plans = [
                *version_past_plans,
                *[
                    active_plan
                    for active_label, active_plan in active_plans_by_label.items()
                    if active_label not in past_labels
                ],
            ]
            start_date = min(p.start_date for p in plans)
            end_date = max(p.end_date for p in plans)
            planned_total_cases = sum(p.planned_total_cases for p in plans)
            daily_map: dict[date, int] = defaultdict(int)
            for plan in plans:
                for d, count in daily_by_plan.get(plan.id, {}).items():
                    daily_map[d] += count

            cumsum = 0
            series_items: list[PastPlanSeriesItem] = []
            for d in _date_range(start_date, end_date):
                cnt = daily_map.get(d, 0)
                cumsum += cnt
                series_items.append(PastPlanSeriesItem(
                    date=d,
                    planned_remaining=planned_total_cases - cumsum,
                    planned_completed_daily=cnt,
                ))
            result.append(PastPlanSeries(
                plan_id=min(p.id for p in version_past_plans),
                version=version,
                label=None,
                reason=None,
                planned_total_cases=planned_total_cases,
                series=series_items,
            ))
        return result

    for plan in past_plans:
        dm = daily_by_plan.get(plan.id, {})
        dates = _date_range(plan.start_date, plan.end_date)
        cumsum = 0
        series_items: list[PastPlanSeriesItem] = []
        for d in dates:
            cnt = dm.get(d, 0)
            cumsum += cnt
            series_items.append(PastPlanSeriesItem(
                date=d,
                planned_remaining=plan.planned_total_cases - cumsum,
                planned_completed_daily=cnt,
            ))
        result.append(PastPlanSeries(
            plan_id=plan.id,
            version=plan.version,
            label=plan.label,
            reason=plan.reason,
            planned_total_cases=plan.planned_total_cases,
            series=series_items,
        ))
    return result


# ---------- メイン ----------

def get_pb_chart(
    db: Session,
    testing_id: int,
    label: str | None = None,
    include_past_plans: bool = False,
) -> PbChartResponse:
    # プロジェクト存在確認
    project = db.scalar(select(Project).where(Project.testing_id == testing_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")

    # 有効な計画
    active_plans = _get_active_plans(db, testing_id, label)
    has_plan = bool(active_plans)

    plan_start: date | None = min(p.start_date for p in active_plans) if has_plan else None
    plan_end: date | None = max(p.end_date for p in active_plans) if has_plan else None
    planned_total: int | None = sum(p.planned_total_cases for p in active_plans) if has_plan else None

    plan_daily_map: dict[date, int] = {}
    plan_remaining_map: dict[date, int] = {}
    plan_d_map: dict[date, int] = {}
    if has_plan:
        plan_daily_map = _get_plan_daily_map(db, [p.id for p in active_plans])
        plan_remaining_map, plan_d_map = _compute_plan_series(
            active_plans, plan_daily_map, plan_start, plan_end, planned_total  # type: ignore[arg-type]
        )

    # 実績
    actual_daily_map = _get_actual_daily_map(db, testing_id, label)
    actual_available_cases, actuals_updated_at = _get_actual_metadata(db, testing_id, label)
    actual_labels = _get_actual_labels(db, testing_id, label)
    plan_only_available_cases = _compute_plan_only_available_cases(active_plans, actual_labels)
    available_cases = actual_available_cases + plan_only_available_cases

    # 不具合
    # - test_result ソース: スナップショットは label 別に保持しているため、表示対象のテスト別に描画できる。
    #   (全て)=label=None のときは全 label を日付ごとに合算する。
    # - azure_devops ソース: チケットはテストに紐付かないため、従来どおり (全て) 表示時のみ描画する。
    bug_count_source = project.bug_count_source
    test_result_bug_daily_map: dict[date, tuple[int, int, int]] = {}
    bug_from = bug_to = None
    if bug_count_source == "test_result":
        test_result_bug_daily_map = _get_test_result_bug_daily_map(db, testing_id, label)
        bugs_present, bugs_updated_at = _get_test_result_bug_metadata(db, testing_id)
        bugs_visible = bool(test_result_bug_daily_map)         # 表示中の label に不具合があるか
        if bugs_visible:
            bug_from = min(test_result_bug_daily_map)
            bug_to = max(test_result_bug_daily_map)
    else:
        bugs_present, bugs_updated_at, bug_from, bug_to = get_bug_chart_metadata(db, testing_id)
        bugs_visible = bugs_present and label is None
        if not bugs_visible:
            bug_from = bug_to = None

    # 日付レンジ
    # Default to the visible PB chart range based on plan/actual series.
    # Bug-only dates are used only when there is no plan or actual data.
    plan_actual_from: date | None = None
    plan_actual_to: date | None = None
    if has_plan:
        plan_actual_from = plan_start
        plan_actual_to = plan_end
    if actual_daily_map:
        actual_min = min(actual_daily_map)
        actual_max = max(actual_daily_map)
        plan_actual_from = min(plan_actual_from, actual_min) if plan_actual_from else actual_min
        plan_actual_to = max(plan_actual_to, actual_max) if plan_actual_to else actual_max

    if (
        project.pb_chart_range_source == "project_period"
        and project.planned_start_date is not None
        and project.planned_end_date is not None
    ):
        range_from = project.planned_start_date
        range_to = project.planned_end_date
    else:
        range_from = plan_actual_from
        range_to = plan_actual_to

    if range_from is None and bug_from is not None:
        range_from = bug_from
        range_to = bug_to

    if range_from is None or range_to is None:
        # データが一切ない
        return PbChartResponse(
            testing_id=testing_id,
            label=label,
            bug_count_source=bug_count_source,
            range=None,
            actuals_updated_at=actuals_updated_at,
            available_cases=0,
            planned_total_cases=None,
            series=[],
            past_plans=[],
            has_bugs=bugs_present,
            bugs_updated_at=bugs_updated_at,
        )

    date_list = _date_range(range_from, range_to)
    actual_remaining_sparse = _compute_actual_series(actual_daily_map, available_cases)
    if not actual_daily_map and plan_only_available_cases > 0:
        actual_remaining_sparse = {d: available_cases for d in date_list}

    bug_cumulative = None
    if bugs_visible:
        if bug_count_source == "test_result":
            bug_series_start = min(bug_from, range_from) if bug_from is not None else range_from
            bug_cumulative = _compute_test_result_bug_series(
                _date_range(bug_series_start, range_to),
                test_result_bug_daily_map,
            )
        else:
            suspend_states = get_settings().azure_devops_bug_suspend_status_set
            bug_cumulative = get_bug_cumulative(db, testing_id, date_list, suspend_states)
    series = _build_series(
        date_list, plan_remaining_map, plan_d_map, actual_remaining_sparse, actual_daily_map,
        bug_cumulative,
    )

    past_plans = _compute_past_plans(db, testing_id, label) if include_past_plans else []

    return PbChartResponse(
        testing_id=testing_id,
        label=label,
        bug_count_source=bug_count_source,
        range={"from": range_from.isoformat(), "to": range_to.isoformat()},
        actuals_updated_at=actuals_updated_at,
        available_cases=available_cases,
        planned_total_cases=planned_total,
        series=series,
        past_plans=past_plans,
        has_bugs=bugs_present,
        bugs_updated_at=bugs_updated_at,
    )
