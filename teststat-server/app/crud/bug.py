from datetime import date, datetime
from urllib.parse import quote

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.bug import BugSnapshot
from app.models.progress import TestResultBugSnapshot
from app.schemas.bug import BugSyncResponse, OpenBugItem
from app.services.azure_devops import BugWorkItem


def _is_suspended(state: str | None, suspend_states: set[str]) -> bool:
    return state is not None and state in suspend_states


def replace_bugs(
    db: Session,
    testing_id: int,
    bugs: list[BugWorkItem],
    suspend_states: set[str],
    fetched_at: datetime,
) -> BugSyncResponse:
    """Testing ID 単位で洗替（delete → insert）し、現時点のカテゴリ別件数を返す。"""
    db.execute(delete(BugSnapshot).where(BugSnapshot.testing_id == testing_id))
    db.add_all(
        BugSnapshot(
            testing_id=testing_id,
            bug_work_item_id=bug.work_item_id,
            title=bug.title or None,
            state=bug.state or None,
            created_date=bug.created_date,
            finish_date=bug.finish_date,
            fetched_at=fetched_at,
        )
        for bug in bugs
    )
    db.commit()

    open_count = suspended_count = resolved_count = 0
    for bug in bugs:
        if _is_suspended(bug.state, suspend_states):
            suspended_count += 1
        elif bug.finish_date is None:
            open_count += 1
        else:
            resolved_count += 1

    return BugSyncResponse(
        testing_id=testing_id,
        fetched=len(bugs),
        open_count=open_count,
        suspended_count=suspended_count,
        resolved_count=resolved_count,
        fetched_at=fetched_at,
    )


def get_bug_cumulative(
    db: Session,
    testing_id: int,
    date_range: list[date],
    suspend_states: set[str],
) -> dict[date, tuple[int, int, int]]:
    """日付ごとの (未解消 open, 対応見送り suspended, 完了 resolved) を返す。

    検出累積(d)  = created_date <= d
    見送り累積(d) = state∈suspend かつ finish_date<=d
    完了累積(d)   = state∉suspend かつ finish_date<=d
    未解消(d)     = 検出累積(d) - 見送り累積(d) - 完了累積(d)
    """
    rows = db.execute(
        select(BugSnapshot.state, BugSnapshot.created_date, BugSnapshot.finish_date).where(
            BugSnapshot.testing_id == testing_id
        )
    ).all()

    result: dict[date, tuple[int, int, int]] = {}
    for d in date_range:
        detected = suspended = resolved = 0
        for state, created_date, finish_date in rows:
            if created_date is not None and created_date <= d:
                detected += 1
            if _is_suspended(state, suspend_states):
                suspended_date = finish_date or created_date
                if suspended_date is not None and suspended_date <= d:
                    suspended += 1
            elif finish_date is not None and finish_date <= d:
                resolved += 1
        result[d] = (detected - suspended - resolved, suspended, resolved)
    return result


def has_bugs(db: Session, testing_id: int) -> bool:
    return db.scalar(
        select(func.count()).select_from(BugSnapshot).where(BugSnapshot.testing_id == testing_id)
    ) > 0


def delete_bug_count_data(db: Session, testing_id: int) -> tuple[int, int]:
    """Testing ID に紐づく取得済み不具合数データを削除する。

    戻り値は (Azure DevOps 由来の削除件数, テスト結果由来の削除件数)。
    """
    azure_result = db.execute(delete(BugSnapshot).where(BugSnapshot.testing_id == testing_id))
    test_result = db.execute(
        delete(TestResultBugSnapshot).where(TestResultBugSnapshot.testing_id == testing_id)
    )
    db.commit()
    return azure_result.rowcount or 0, test_result.rowcount or 0


def get_bugs_updated_at(db: Session, testing_id: int) -> datetime | None:
    return db.scalar(
        select(func.max(BugSnapshot.fetched_at)).where(BugSnapshot.testing_id == testing_id)
    )


def get_bug_date_bounds(db: Session, testing_id: int) -> tuple[date | None, date | None]:
    """range 拡張用に、起票日の最小と (起票日/完了日) の最大を返す。"""
    min_created = db.scalar(
        select(func.min(BugSnapshot.created_date)).where(BugSnapshot.testing_id == testing_id)
    )
    max_created = db.scalar(
        select(func.max(BugSnapshot.created_date)).where(BugSnapshot.testing_id == testing_id)
    )
    max_finish = db.scalar(
        select(func.max(BugSnapshot.finish_date)).where(BugSnapshot.testing_id == testing_id)
    )
    max_date = max((d for d in (max_created, max_finish) if d is not None), default=None)
    return min_created, max_date


def get_open_bugs(
    db: Session,
    testing_id: int,
    settings: Settings,
    suspend_states: set[str],
) -> list[OpenBugItem]:
    rows = db.execute(
        select(BugSnapshot.bug_work_item_id, BugSnapshot.title, BugSnapshot.state)
        .where(
            BugSnapshot.testing_id == testing_id,
            (BugSnapshot.finish_date.is_(None) | BugSnapshot.state.in_(suspend_states)),
        )
        .order_by(BugSnapshot.bug_work_item_id)
    ).all()
    return [
        OpenBugItem(
            work_item_id=work_item_id,
            title=title,
            state=state,
            url=build_work_item_url(work_item_id, settings),
            is_suspended=_is_suspended(state, suspend_states),
        )
        for work_item_id, title, state in rows
    ]


def build_work_item_url(work_item_id: int, settings: Settings) -> str | None:
    if not settings.azure_devops_organization:
        return None
    org = quote(settings.azure_devops_organization.strip("/"), safe="")
    project = settings.azure_devops_project.strip("/")
    if project:
        return f"https://dev.azure.com/{org}/{quote(project, safe='')}/_workitems/edit/{work_item_id}"
    return f"https://dev.azure.com/{org}/_workitems/edit/{work_item_id}"
