from collections import defaultdict
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.plan import PlanLabel
from app.models.project import Project
from app.models.progress import DailyPersonProgress, DailyProgress, FileProgress, TestResultBugSnapshot, Testing
from app.schemas.progress import DailyProgressItem, ProgressPostResponse, ProgressRequest, ProgressSummaryResponse, ResultCounts, SummaryCounts


PLAN_LABEL_OPTION_FIELDS = (
    "subtask_id",
    "target_sheets",
    "ignore_sheets",
    "include_hidden_sheets",
    "target_environments",
    "ignore_environments",
)


def _validate_replace_payload(payload: ProgressRequest) -> None:
    if not payload.files:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="files must not be empty")
    if all(file.available_cases == 0 for file in payload.files):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="all files have zero available cases")
    if all(bool(file.error) for file in payload.files):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="all files contain errors")


def _get_or_create_testing(db: Session, testing_id: int, project_name: str) -> Testing:
    testing = db.scalar(select(Testing).where(Testing.testing_id == testing_id))
    if testing is None:
        testing = Testing(testing_id=testing_id, project_name=project_name)
        db.add(testing)
        db.flush()
    else:
        testing.project_name = project_name
        testing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return testing


def _ensure_project_accepts_progress(db: Session, testing_id: int) -> None:
    project = db.scalar(select(Project).where(Project.testing_id == testing_id))
    if project is not None and project.archived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="archived project cannot accept progress updates",
        )


def _sync_plan_label_metadata(db: Session, payload: ProgressRequest) -> None:
    updates_by_label: dict[str, dict[str, object]] = {}
    for file in payload.files:
        label = file.label.strip() if file.label else ""
        if not label:
            continue

        updates = updates_by_label.setdefault(label, {})
        if file.source_url and "source_url" not in updates:
            updates["source_url"] = file.source_url
        for field in PLAN_LABEL_OPTION_FIELDS:
            if field in file.model_fields_set and field not in updates:
                updates[field] = getattr(file, field)

    for label, updates in updates_by_label.items():
        if not updates:
            continue
        plan_label = db.scalar(
            select(PlanLabel).where(
                PlanLabel.testing_id == payload.testing_id,
                PlanLabel.label == label,
            )
        )
        if plan_label is None:
            max_display_order = db.scalar(
                select(func.max(PlanLabel.display_order)).where(PlanLabel.testing_id == payload.testing_id)
            )
            db.add(
                PlanLabel(
                    testing_id=payload.testing_id,
                    label=label,
                    display_order=(max_display_order + 1) if max_display_order is not None else 0,
                    **updates,
                )
            )
        else:
            for field, value in updates.items():
                setattr(plan_label, field, value)


def replace_progress(db: Session, payload: ProgressRequest) -> ProgressPostResponse:
    _validate_replace_payload(payload)
    _ensure_project_accepts_progress(db, payload.testing_id)

    _get_or_create_testing(db, payload.testing_id, payload.project_name)
    _sync_plan_label_metadata(db, payload)

    db.execute(delete(FileProgress).where(FileProgress.testing_id == payload.testing_id))
    db.execute(delete(DailyProgress).where(DailyProgress.testing_id == payload.testing_id))
    db.execute(delete(DailyPersonProgress).where(DailyPersonProgress.testing_id == payload.testing_id))

    file_rows: list[FileProgress] = []
    daily_rows: list[DailyProgress] = []
    person_rows: list[DailyPersonProgress] = []
    # (label, date) -> [fail, suspend, fixed]。label 別に不具合バーンダウンを蓄積するため。
    bug_counts_by_label_date: dict[tuple[str | None, date], list[int]] = defaultdict(lambda: [0, 0, 0])

    for file in payload.files:
        file_rows.append(
            FileProgress(
                testing_id=payload.testing_id,
                file_name=file.file_name,
                label=file.label,
                environment=file.environment,
                total_cases=file.total_cases,
                available_cases=file.available_cases,
                excluded_cases=file.excluded_cases,
                completed=file.completed,
                executed=file.executed,
                not_run=file.not_run,
                completed_rate=file.completed_rate,
                executed_rate=file.executed_rate,
                result_pass=file.results.pass_count,
                result_fixed=file.results.fixed,
                result_fail=file.results.fail,
                result_blocked=file.results.blocked,
                result_suspend=file.results.suspend,
                result_na=file.results.na,
                start_date=file.start_date,
                latest_update=file.latest_update,
                sent_at=payload.sent_at,
            )
        )
        for daily in file.daily:
            bug_counts = bug_counts_by_label_date[(file.label, daily.date)]
            bug_counts[0] += daily.fail
            bug_counts[1] += daily.suspend
            bug_counts[2] += daily.fixed
            daily_rows.append(
                DailyProgress(
                    testing_id=payload.testing_id,
                    file_name=file.file_name,
                    label=file.label,
                    environment=file.environment,
                    date=daily.date,
                    result_pass=daily.pass_count,
                    result_fixed=daily.fixed,
                    result_fail=daily.fail,
                    result_blocked=daily.blocked,
                    result_suspend=daily.suspend,
                    result_na=daily.na,
                    completed=daily.completed,
                    executed=daily.executed,
                    planned=daily.planned,
                )
            )
        for person in file.by_person:
            if person.person.strip():
                person_rows.append(
                    DailyPersonProgress(
                        testing_id=payload.testing_id,
                        file_name=file.file_name,
                        label=file.label,
                        environment=file.environment,
                        date=person.date,
                        person=person.person,
                        count=person.count,
                    )
                )

    db.add_all(file_rows + daily_rows + person_rows)

    _merge_test_result_bug_snapshots(db, payload.testing_id, bug_counts_by_label_date, payload.sent_at)
    db.commit()

    return ProgressPostResponse(
        testing_id=payload.testing_id,
        inserted_files=len(file_rows),
        inserted_daily_rows=len(daily_rows),
        inserted_person_rows=len(person_rows),
    )


def _merge_test_result_bug_snapshots(
    db: Session,
    testing_id: int,
    new_counts_by_label_date: dict[tuple[str | None, date], list[int]],
    sent_at: datetime,
) -> None:
    """テスト結果由来の不具合スナップショットを label（テスト種別）別にバーンダウン用に蓄積する。

    new_counts_by_label_date: {(label, date): [fail, suspend, fixed]} … 今回取り込みの label×日付別件数。

    detected_count（検出増分）は「総不具合数(Fail+Suspend+Fixed)累積の最大値（ハイウォーターマーク）」
    として保持し、再取込で減らさない（= 検出履歴を残す。結果が変わって日付が移動しても消えない）。
    suspend_count / fixed_count は今回取り込みの現在値で置き換える（状態が変われば見送り／完了から外れる）。
    ハイウォーターマークは label ごとに独立して算出する。
    """
    existing = db.scalars(
        select(TestResultBugSnapshot)
        .where(TestResultBugSnapshot.testing_id == testing_id)
        .order_by(TestResultBugSnapshot.snapshot_date)
    ).all()
    old_detected_by_label_date: dict[str | None, dict[date, int]] = defaultdict(dict)
    for row in existing:
        old_detected_by_label_date[row.label][row.snapshot_date] = row.detected_count

    # 今回取り込みを label ごとにまとめ直す。
    new_by_label: dict[str | None, dict[date, list[int]]] = defaultdict(dict)
    for (label, d), counts in new_counts_by_label_date.items():
        new_by_label[label][d] = counts

    merged_rows: list[tuple[str | None, date, tuple[int, int, int]]] = []
    for label in set(old_detected_by_label_date) | set(new_by_label):
        old_detected_by_date = old_detected_by_label_date.get(label, {})
        new_counts_by_date = new_by_label.get(label, {})

        new_total_by_date = {d: c[0] + c[1] + c[2] for d, c in new_counts_by_date.items()}
        new_suspend_by_date = {d: c[1] for d, c in new_counts_by_date.items()}
        new_fixed_by_date = {d: c[2] for d, c in new_counts_by_date.items()}

        all_dates = sorted(set(old_detected_by_date) | set(new_counts_by_date))

        # ハイウォーターマージ: 検出累積(d) = max(既存検出累積(d), 今回総数累積(d))。
        # 同一不具合が日付移動しても二重計上せず、検出済み件数は減らない。
        old_cum = new_cum = prev_hw = 0
        for d in all_dates:
            old_cum += old_detected_by_date.get(d, 0)
            new_cum += new_total_by_date.get(d, 0)
            hw = max(old_cum, new_cum)
            merged_rows.append(
                (label, d, (hw - prev_hw, new_suspend_by_date.get(d, 0), new_fixed_by_date.get(d, 0)))
            )
            prev_hw = hw

    # 既存の検出累積は merged_rows に畳み込み済みなので全件入れ替え。
    # 何も寄与しない行（検出0・見送り0・完了0）は保存しない。
    db.execute(delete(TestResultBugSnapshot).where(TestResultBugSnapshot.testing_id == testing_id))
    db.add_all(
        TestResultBugSnapshot(
            testing_id=testing_id,
            label=label,
            snapshot_date=d,
            detected_count=detected,
            suspend_count=suspend,
            fixed_count=fixed,
            sent_at=sent_at,
        )
        for label, d, (detected, suspend, fixed) in merged_rows
        if detected or suspend or fixed
    )


def get_progress_summary(db: Session, testing_id: int) -> ProgressSummaryResponse | None:
    testing = db.scalar(select(Testing).where(Testing.testing_id == testing_id))
    if testing is None:
        return None

    totals = db.execute(
        select(
            func.coalesce(func.sum(FileProgress.total_cases), 0),
            func.coalesce(func.sum(FileProgress.available_cases), 0),
            func.coalesce(func.sum(FileProgress.completed), 0),
            func.coalesce(func.sum(FileProgress.executed), 0),
            func.coalesce(func.sum(FileProgress.result_pass), 0),
            func.coalesce(func.sum(FileProgress.result_fixed), 0),
            func.coalesce(func.sum(FileProgress.result_fail), 0),
            func.coalesce(func.sum(FileProgress.result_blocked), 0),
            func.coalesce(func.sum(FileProgress.result_suspend), 0),
            func.coalesce(func.sum(FileProgress.result_na), 0),
        ).where(FileProgress.testing_id == testing_id)
    ).one()
    total_cases, available_cases, completed, executed, passed, fixed, fail, blocked, suspend, na = totals
    completed_rate = round((completed / available_cases * 100), 2) if available_cases else 0
    executed_rate = round((executed / available_cases * 100), 2) if available_cases else 0

    return ProgressSummaryResponse(
        testing_id=testing.testing_id,
        project_name=testing.project_name,
        updated_at=testing.updated_at,
        summary=SummaryCounts(
            total_cases=total_cases,
            available_cases=available_cases,
            completed=completed,
            executed=executed,
            completed_rate=completed_rate,
            executed_rate=executed_rate,
        ),
        results=ResultCounts(
            pass_count=passed,
            fixed=fixed,
            fail=fail,
            blocked=blocked,
            suspend=suspend,
            na=na,
        ),
    )


def get_file_progress(db: Session, testing_id: int) -> list[FileProgress]:
    return list(db.scalars(select(FileProgress).where(FileProgress.testing_id == testing_id).order_by(FileProgress.file_name, FileProgress.label)))


def get_daily_progress(db: Session, testing_id: int) -> list[DailyProgressItem]:
    rows = db.scalars(select(DailyProgress).where(DailyProgress.testing_id == testing_id).order_by(DailyProgress.date, DailyProgress.file_name, DailyProgress.label)).all()
    return [
        DailyProgressItem(
            date=row.date,
            file_name=row.file_name,
            label=row.label,
            environment=row.environment,
            completed=row.completed,
            executed=row.executed,
            planned=row.planned,
            pass_count=row.result_pass,
            fixed=row.result_fixed,
            fail=row.result_fail,
            blocked=row.result_blocked,
            suspend=row.result_suspend,
            na=row.result_na,
        )
        for row in rows
    ]


def list_testings(db: Session) -> list[Testing]:
    return list(db.scalars(select(Testing).order_by(Testing.updated_at.desc(), Testing.testing_id)))
