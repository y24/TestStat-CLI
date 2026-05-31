from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanDaily
from app.models.progress import DailyProgress, FileProgress, Testing
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


ActualSummary = tuple[int, int, float, bool]


def _active_plan_count(db: Session, testing_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Plan)
        .where(Plan.testing_id == testing_id, Plan.is_active.is_(True))
    ) or 0


def _actual_summary(db: Session, testing_id: int) -> ActualSummary:
    available_cases, completed, file_count, min_completed_rate = db.execute(
        select(
            func.coalesce(func.sum(FileProgress.available_cases), 0),
            func.coalesce(func.sum(FileProgress.completed), 0),
            func.count(FileProgress.id),
            func.min(FileProgress.completed_rate),
        ).where(FileProgress.testing_id == testing_id)
    ).one()
    completed_rate = round((completed / available_cases * 100), 2) if available_cases else 0
    actual_all_completed = bool(file_count and min_completed_rate is not None and min_completed_rate >= 100)
    return int(available_cases), int(completed), completed_rate, actual_all_completed


def _actual_vs_plan_rate(db: Session, testing_id: int) -> float | None:
    latest_actual_date = db.scalar(
        select(func.max(DailyProgress.date)).where(DailyProgress.testing_id == testing_id)
    )
    if latest_actual_date is None:
        return None

    actual_executed = db.scalar(
        select(func.coalesce(func.sum(DailyProgress.executed), 0)).where(
            DailyProgress.testing_id == testing_id,
            DailyProgress.date <= latest_actual_date,
        )
    ) or 0
    planned_completed = db.scalar(
        select(func.coalesce(func.sum(PlanDaily.planned_count), 0))
        .join(Plan, PlanDaily.plan_id == Plan.id)
        .where(
            Plan.testing_id == testing_id,
            Plan.is_active.is_(True),
            PlanDaily.date <= latest_actual_date,
        )
    ) or 0
    if planned_completed <= 0:
        return None
    return round(actual_executed / planned_completed * 100, 2)


def _actual_summaries(db: Session, testing_ids: list[int]) -> dict[int, ActualSummary]:
    rows = db.execute(
        select(
            FileProgress.testing_id,
            func.coalesce(func.sum(FileProgress.available_cases), 0),
            func.coalesce(func.sum(FileProgress.completed), 0),
            func.count(FileProgress.id),
            func.min(FileProgress.completed_rate),
        )
        .where(FileProgress.testing_id.in_(testing_ids))
        .group_by(FileProgress.testing_id)
    ).all()
    summaries: dict[int, ActualSummary] = {}
    for testing_id, available_cases, completed, file_count, min_completed_rate in rows:
        completed_rate = round((completed / available_cases * 100), 2) if available_cases else 0
        actual_all_completed = bool(file_count and min_completed_rate is not None and min_completed_rate >= 100)
        summaries[testing_id] = (int(available_cases), int(completed), completed_rate, actual_all_completed)
    return summaries


def _actual_vs_plan_rates(db: Session, testing_ids: list[int]) -> dict[int, float | None]:
    return {testing_id: _actual_vs_plan_rate(db, testing_id) for testing_id in testing_ids}


def _to_response(
    project: Project,
    testing: Testing | None,
    active_plan_count: int = 0,
    actual_summary: ActualSummary = (0, 0, 0, False),
    actual_vs_plan_rate: float | None = None,
) -> ProjectResponse:
    actual_available_cases, actual_completed, actual_completed_rate, actual_all_completed = actual_summary
    return ProjectResponse(
        testing_id=project.testing_id,
        name=project.name,
        ticket_ref=project.ticket_ref,
        archived=project.archived,
        created_at=project.created_at,
        updated_at=project.updated_at,
        has_actuals=testing is not None,
        actuals_updated_at=testing.updated_at if testing else None,
        actual_available_cases=actual_available_cases,
        actual_completed=actual_completed,
        actual_completed_rate=actual_completed_rate,
        actual_vs_plan_rate=actual_vs_plan_rate,
        actual_all_completed=actual_all_completed,
        active_plan_count=active_plan_count,
    )


def _get_testing(db: Session, testing_id: int) -> Testing | None:
    return db.scalar(select(Testing).where(Testing.testing_id == testing_id))


def list_projects(db: Session) -> list[ProjectResponse]:
    projects = list(db.scalars(select(Project).order_by(Project.archived, Project.updated_at.desc())))
    if not projects:
        return []
    tids = [p.testing_id for p in projects]
    testings = {t.testing_id: t for t in db.scalars(select(Testing).where(Testing.testing_id.in_(tids)))}
    plan_counts = dict(
        db.execute(
            select(Plan.testing_id, func.count())
            .where(Plan.testing_id.in_(tids), Plan.is_active.is_(True))
            .group_by(Plan.testing_id)
        ).all()
    )
    actual_summaries = _actual_summaries(db, tids)
    actual_vs_plan_rates = _actual_vs_plan_rates(db, tids)
    return [
        _to_response(
            p,
            testings.get(p.testing_id),
            plan_counts.get(p.testing_id, 0),
            actual_summaries.get(p.testing_id, (0, 0, 0, False)),
            actual_vs_plan_rates.get(p.testing_id),
        )
        for p in projects
    ]


def get_project(db: Session, testing_id: int) -> ProjectResponse:
    project = db.scalar(select(Project).where(Project.testing_id == testing_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return _to_response(
        project,
        _get_testing(db, testing_id),
        _active_plan_count(db, testing_id),
        _actual_summary(db, testing_id),
        _actual_vs_plan_rate(db, testing_id),
    )


def create_project(db: Session, payload: ProjectCreate) -> ProjectResponse:
    existing = db.scalar(select(Project).where(Project.testing_id == payload.testing_id))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Testing ID {payload.testing_id} は既に登録されています",
        )
    project = Project(
        testing_id=payload.testing_id,
        name=payload.name,
        ticket_ref=payload.ticket_ref,
    )
    db.add(project)
    db.commit()
    return _to_response(
        project,
        _get_testing(db, payload.testing_id),
        0,
        _actual_summary(db, payload.testing_id),
        _actual_vs_plan_rate(db, payload.testing_id),
    )


def update_project(db: Session, testing_id: int, payload: ProjectUpdate) -> ProjectResponse:
    project = db.scalar(select(Project).where(Project.testing_id == testing_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    if payload.name is not None:
        project.name = payload.name
    if payload.ticket_ref is not None:
        project.ticket_ref = payload.ticket_ref
    if payload.archived is not None:
        project.archived = payload.archived
    project.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return _to_response(
        project,
        _get_testing(db, testing_id),
        _active_plan_count(db, testing_id),
        _actual_summary(db, testing_id),
        _actual_vs_plan_rate(db, testing_id),
    )


def delete_project(db: Session, testing_id: int) -> None:
    project = db.scalar(select(Project).where(Project.testing_id == testing_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    if project.archived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="archived project cannot be deleted",
        )
    db.delete(project)
    db.commit()
