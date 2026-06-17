from collections import defaultdict
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.progress import DailyPersonProgress, DailyProgress, FileProgress, TestResultBugSnapshot, Testing
from app.schemas.progress import DailyProgressItem, ProgressPostResponse, ProgressRequest, ProgressSummaryResponse, ResultCounts, SummaryCounts


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


def replace_progress(db: Session, payload: ProgressRequest) -> ProgressPostResponse:
    _validate_replace_payload(payload)
    _ensure_project_accepts_progress(db, payload.testing_id)

    _get_or_create_testing(db, payload.testing_id, payload.project_name)

    db.execute(delete(FileProgress).where(FileProgress.testing_id == payload.testing_id))
    db.execute(delete(DailyProgress).where(DailyProgress.testing_id == payload.testing_id))
    db.execute(delete(DailyPersonProgress).where(DailyPersonProgress.testing_id == payload.testing_id))
    db.execute(delete(TestResultBugSnapshot).where(TestResultBugSnapshot.testing_id == payload.testing_id))

    file_rows: list[FileProgress] = []
    daily_rows: list[DailyProgress] = []
    person_rows: list[DailyPersonProgress] = []
    bug_counts_by_date: dict[date, list[int]] = defaultdict(lambda: [0, 0, 0])

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
                sender=payload.sender,
                sent_at=payload.sent_at,
            )
        )
        for daily in file.daily:
            bug_counts = bug_counts_by_date[daily.date]
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
    db.add_all(
        TestResultBugSnapshot(
            testing_id=payload.testing_id,
            snapshot_date=snapshot_date,
            fail_count=counts[0],
            suspend_count=counts[1],
            fixed_count=counts[2],
            sent_at=payload.sent_at,
        )
        for snapshot_date, counts in bug_counts_by_date.items()
    )
    db.commit()

    return ProgressPostResponse(
        testing_id=payload.testing_id,
        inserted_files=len(file_rows),
        inserted_daily_rows=len(daily_rows),
        inserted_person_rows=len(person_rows),
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
