from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.progress import Testing
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


def _active_plan_count(db: Session, testing_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Plan)
        .where(Plan.testing_id == testing_id, Plan.is_active.is_(True))
    ) or 0


def _to_response(project: Project, testing: Testing | None, active_plan_count: int = 0) -> ProjectResponse:
    return ProjectResponse(
        testing_id=project.testing_id,
        name=project.name,
        ticket_ref=project.ticket_ref,
        archived=project.archived,
        created_at=project.created_at,
        updated_at=project.updated_at,
        has_actuals=testing is not None,
        actuals_updated_at=testing.updated_at if testing else None,
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
    return [_to_response(p, testings.get(p.testing_id), plan_counts.get(p.testing_id, 0)) for p in projects]


def get_project(db: Session, testing_id: int) -> ProjectResponse:
    project = db.scalar(select(Project).where(Project.testing_id == testing_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return _to_response(project, _get_testing(db, testing_id), _active_plan_count(db, testing_id))


def create_project(db: Session, payload: ProjectCreate) -> ProjectResponse:
    existing = db.scalar(select(Project).where(Project.testing_id == payload.testing_id))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"testing_id {payload.testing_id} は既に登録されています",
        )
    project = Project(
        testing_id=payload.testing_id,
        name=payload.name,
        ticket_ref=payload.ticket_ref,
    )
    db.add(project)
    db.commit()
    return _to_response(project, _get_testing(db, payload.testing_id), 0)


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
    return _to_response(project, _get_testing(db, testing_id), _active_plan_count(db, testing_id))


def delete_project(db: Session, testing_id: int) -> None:
    project = db.scalar(select(Project).where(Project.testing_id == testing_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    db.delete(project)
    db.commit()
