from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanDaily, PlanLabel
from app.models.progress import DailyProgress, FileProgress, Testing
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectOrderUpdate, ProjectResponse, ProjectUpdate


ActualSummary = tuple[int, int, float, bool]


def _disabled_labels_subquery(testing_id: int):
    return select(PlanLabel.label).where(
        PlanLabel.testing_id == testing_id,
        PlanLabel.is_disabled.is_(True),
    )


def _enabled_label_condition(label_column, testing_id: int):
    return (label_column.is_(None)) | (label_column.not_in(_disabled_labels_subquery(testing_id)))


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _validate_project_planned_date_range(project: Project) -> None:
    if (
        project.planned_start_date is not None
        and project.planned_end_date is not None
        and project.planned_start_date > project.planned_end_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="planned_start_date must be before or equal to planned_end_date",
        )


def _ensure_archived_project_update_allowed(project: Project, payload: ProjectUpdate) -> None:
    if not project.archived:
        return
    if payload.model_fields_set == {"archived"} and payload.archived is False:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="archived project is read-only",
    )


def _active_plan_count(db: Session, testing_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Plan)
        .where(
            Plan.testing_id == testing_id,
            Plan.is_active.is_(True),
            _enabled_label_condition(Plan.label, testing_id),
        )
    ) or 0


def _plan_actual_offset(db: Session, testing_id: int) -> int:
    """実績未送信で、実績オフセット対象になっている有効計画の件数。"""
    disabled_labels = set(db.scalars(_disabled_labels_subquery(testing_id)))
    actual_labels = set(db.scalars(
        select(FileProgress.label).where(FileProgress.testing_id == testing_id).distinct()
    )) | set(db.scalars(
        select(DailyProgress.label).where(DailyProgress.testing_id == testing_id).distinct()
    ))
    label_settings = {
        item.label: item.use_plan_as_actual_offset
        for item in db.scalars(select(PlanLabel).where(PlanLabel.testing_id == testing_id))
    }
    return sum(
        plan.planned_total_cases
        for plan in db.scalars(select(Plan).where(Plan.testing_id == testing_id, Plan.is_active.is_(True)))
        if plan.label not in disabled_labels
        and plan.label not in actual_labels
        and label_settings.get(plan.label, True)
    )

def _actual_summary(db: Session, testing_id: int) -> ActualSummary:
    available_cases, completed, file_count, min_completed_rate = db.execute(
        select(
            func.coalesce(func.sum(FileProgress.available_cases), 0),
            func.coalesce(func.sum(FileProgress.completed), 0),
            func.count(FileProgress.id),
            func.min(FileProgress.completed_rate),
        ).where(
            FileProgress.testing_id == testing_id,
            _enabled_label_condition(FileProgress.label, testing_id),
        )
    ).one()
    total_cases = available_cases + _plan_actual_offset(db, testing_id)
    completed_rate = round((completed / total_cases * 100), 2) if total_cases else 0
    actual_all_completed = bool(
        total_cases == available_cases and file_count and min_completed_rate is not None and min_completed_rate >= 100
    )
    return int(available_cases), int(completed), completed_rate, actual_all_completed


def _actual_vs_plan_rate(db: Session, testing_id: int) -> float | None:
    latest_actual_date = db.scalar(
        select(func.max(DailyProgress.date)).where(
            DailyProgress.testing_id == testing_id,
            _enabled_label_condition(DailyProgress.label, testing_id),
        )
    )
    if latest_actual_date is None:
        return None

    actual_executed = db.scalar(
        select(func.coalesce(func.sum(DailyProgress.executed), 0)).where(
            DailyProgress.testing_id == testing_id,
            DailyProgress.date <= latest_actual_date,
            _enabled_label_condition(DailyProgress.label, testing_id),
        )
    ) or 0
    planned_completed = db.scalar(
        select(func.coalesce(func.sum(PlanDaily.planned_count), 0))
        .join(Plan, PlanDaily.plan_id == Plan.id)
        .where(
            Plan.testing_id == testing_id,
            Plan.is_active.is_(True),
            PlanDaily.date <= latest_actual_date,
            _enabled_label_condition(Plan.label, testing_id),
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
        .outerjoin(
            PlanLabel,
            (PlanLabel.testing_id == FileProgress.testing_id) & (PlanLabel.label == FileProgress.label),
        )
        .where((PlanLabel.id.is_(None)) | (PlanLabel.is_disabled.is_(False)))
        .group_by(FileProgress.testing_id)
    ).all()
    summaries: dict[int, ActualSummary] = {}
    for testing_id, available_cases, completed, file_count, min_completed_rate in rows:
        total_cases = available_cases + _plan_actual_offset(db, testing_id)
        completed_rate = round((completed / total_cases * 100), 2) if total_cases else 0
        actual_all_completed = bool(
            total_cases == available_cases and file_count and min_completed_rate is not None and min_completed_rate >= 100
        )
        summaries[testing_id] = (int(available_cases), int(completed), completed_rate, actual_all_completed)
    return summaries


def _actual_vs_plan_rates(db: Session, testing_ids: list[int]) -> dict[int, float | None]:
    if not testing_ids:
        return {}

    latest_actual_dates = (
        select(
            DailyProgress.testing_id.label("testing_id"),
            func.max(DailyProgress.date).label("latest_actual_date"),
        )
        .where(DailyProgress.testing_id.in_(testing_ids))
        .outerjoin(
            PlanLabel,
            (PlanLabel.testing_id == DailyProgress.testing_id) & (PlanLabel.label == DailyProgress.label),
        )
        .where((PlanLabel.id.is_(None)) | (PlanLabel.is_disabled.is_(False)))
        .group_by(DailyProgress.testing_id)
        .subquery()
    )

    actual_rows = db.execute(
        select(
            DailyProgress.testing_id,
            func.coalesce(func.sum(DailyProgress.executed), 0),
        )
        .join(
            latest_actual_dates,
            DailyProgress.testing_id == latest_actual_dates.c.testing_id,
        )
        .where(DailyProgress.date <= latest_actual_dates.c.latest_actual_date)
        .outerjoin(
            PlanLabel,
            (PlanLabel.testing_id == DailyProgress.testing_id) & (PlanLabel.label == DailyProgress.label),
        )
        .where((PlanLabel.id.is_(None)) | (PlanLabel.is_disabled.is_(False)))
        .group_by(DailyProgress.testing_id)
    ).all()
    actuals = {testing_id: executed for testing_id, executed in actual_rows}

    planned_rows = db.execute(
        select(
            Plan.testing_id,
            func.coalesce(func.sum(PlanDaily.planned_count), 0),
        )
        .join(PlanDaily, PlanDaily.plan_id == Plan.id)
        .join(
            latest_actual_dates,
            Plan.testing_id == latest_actual_dates.c.testing_id,
        )
        .where(
            Plan.testing_id.in_(testing_ids),
            Plan.is_active.is_(True),
            PlanDaily.date <= latest_actual_dates.c.latest_actual_date,
        )
        .outerjoin(
            PlanLabel,
            (PlanLabel.testing_id == Plan.testing_id) & (PlanLabel.label == Plan.label),
        )
        .where(
            (PlanLabel.id.is_(None)) | (PlanLabel.is_disabled.is_(False)),
        )
        .group_by(Plan.testing_id)
    ).all()
    planned = {testing_id: planned_completed for testing_id, planned_completed in planned_rows}

    rates: dict[int, float | None] = {}
    for testing_id in testing_ids:
        planned_completed = planned.get(testing_id, 0) or 0
        if planned_completed <= 0 or testing_id not in actuals:
            rates[testing_id] = None
        else:
            rates[testing_id] = round((actuals.get(testing_id, 0) or 0) / planned_completed * 100, 2)
    return rates


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
        planned_start_date=project.planned_start_date,
        planned_end_date=project.planned_end_date,
        bug_count_source=project.bug_count_source,
        bug_parent_work_item_id=project.bug_parent_work_item_id,
        bug_work_item_type=project.bug_work_item_type,
        bug_tag=project.bug_tag,
        pb_chart_range_source=project.pb_chart_range_source,
        bug_axis_max=project.bug_axis_max,
        archived=project.archived,
        display_order=project.display_order,
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
    projects = list(
        db.scalars(
            select(Project).order_by(
                Project.archived,
                Project.display_order,
                Project.updated_at.desc(),
                Project.testing_id,
            )
        )
    )
    if not projects:
        return []
    tids = [p.testing_id for p in projects]
    testings = {t.testing_id: t for t in db.scalars(select(Testing).where(Testing.testing_id.in_(tids)))}
    plan_counts = dict(
        db.execute(
            select(Plan.testing_id, func.count())
            .where(Plan.testing_id.in_(tids), Plan.is_active.is_(True))
            .outerjoin(
                PlanLabel,
                (PlanLabel.testing_id == Plan.testing_id) & (PlanLabel.label == Plan.label),
            )
            .where((PlanLabel.id.is_(None)) | (PlanLabel.is_disabled.is_(False)))
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
    max_display_order = db.scalar(select(func.max(Project.display_order)))
    project = Project(
        testing_id=payload.testing_id,
        name=payload.name,
        ticket_ref=payload.ticket_ref,
        planned_start_date=payload.planned_start_date,
        planned_end_date=payload.planned_end_date,
        bug_count_source=payload.bug_count_source,
        bug_parent_work_item_id=payload.bug_parent_work_item_id,
        bug_work_item_type=_blank_to_none(payload.bug_work_item_type),
        bug_tag=_blank_to_none(payload.bug_tag),
        pb_chart_range_source=payload.pb_chart_range_source,
        bug_axis_max=payload.bug_axis_max,
        display_order=(max_display_order + 1) if max_display_order is not None else 0,
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
    _ensure_archived_project_update_allowed(project, payload)
    if payload.name is not None:
        project.name = payload.name
    if payload.ticket_ref is not None:
        project.ticket_ref = payload.ticket_ref
    if "planned_start_date" in payload.model_fields_set:
        project.planned_start_date = payload.planned_start_date
    if "planned_end_date" in payload.model_fields_set:
        project.planned_end_date = payload.planned_end_date
    if payload.bug_count_source is not None:
        project.bug_count_source = payload.bug_count_source
    if "bug_parent_work_item_id" in payload.model_fields_set:
        project.bug_parent_work_item_id = payload.bug_parent_work_item_id
    if "bug_work_item_type" in payload.model_fields_set:
        project.bug_work_item_type = _blank_to_none(payload.bug_work_item_type)
    if "bug_tag" in payload.model_fields_set:
        project.bug_tag = _blank_to_none(payload.bug_tag)
    if payload.pb_chart_range_source is not None:
        project.pb_chart_range_source = payload.pb_chart_range_source
    if "bug_axis_max" in payload.model_fields_set:
        project.bug_axis_max = payload.bug_axis_max
    if payload.archived is not None:
        project.archived = payload.archived
    _validate_project_planned_date_range(project)
    project.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
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


def update_project_order(db: Session, payload: ProjectOrderUpdate) -> list[ProjectResponse]:
    unique_ids = list(dict.fromkeys(payload.testing_ids))
    projects = list(db.scalars(select(Project).where(Project.testing_id.in_(unique_ids))))
    projects_by_id = {project.testing_id: project for project in projects}
    missing_ids = [testing_id for testing_id in unique_ids if testing_id not in projects_by_id]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"project not found: {missing_ids[0]}",
        )

    for index, testing_id in enumerate(unique_ids):
        projects_by_id[testing_id].display_order = index
    db.commit()
    return list_projects(db)
