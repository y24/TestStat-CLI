from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanDaily, PlanLabel
from app.models.project import Project
from app.models.progress import DailyPersonProgress, DailyProgress, FileProgress, TestResultBugSnapshot
from app.schemas.plan import (
    PlanCreate,
    PlanDetail,
    PlanDailyItem,
    PlanItem,
    PlanLabelCreate,
    PlanLabelItem,
    PlanLabelUpdate,
    ProjectLabelUpdate,
)


# ---------- helpers ----------

def _require_project(db: Session, testing_id: int) -> Project:
    p = db.scalar(select(Project).where(Project.testing_id == testing_id))
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return p


def _require_plan(db: Session, plan_id: int) -> Plan:
    p = db.scalar(select(Plan).where(Plan.id == plan_id))
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="plan not found")
    return p


def _require_plan_label(db: Session, label_id: int) -> PlanLabel:
    label = db.scalar(select(PlanLabel).where(PlanLabel.id == label_id))
    if label is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="plan label not found")
    return label


def _label_filter(label: str | None):
    """label が None の場合は IS NULL、それ以外は == を返す。"""
    return Plan.label.is_(None) if label is None else Plan.label == label


def _daily_total(db: Session, plan_id: int) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(PlanDaily.planned_count), 0))
        .where(PlanDaily.plan_id == plan_id)
    ) or 0


def _to_item(plan: Plan, daily_total: int) -> PlanItem:
    return PlanItem(
        id=plan.id,
        testing_id=plan.testing_id,
        label=plan.label,
        version=plan.version,
        is_active=plan.is_active,
        reason=plan.reason,
        planned_total_cases=plan.planned_total_cases,
        start_date=plan.start_date,
        end_date=plan.end_date,
        created_at=plan.created_at,
        created_by=plan.created_by,
        daily_total=daily_total,
    )


def _validate_daily(payload: PlanCreate) -> None:
    dates = [d.date for d in payload.daily]
    if len(dates) != len(set(dates)):
        raise HTTPException(
            status_code=422,
            detail="daily に重複する日付があります",
        )
    for d in payload.daily:
        if not (payload.start_date <= d.date <= payload.end_date):
            raise HTTPException(
                status_code=422,
                detail=f"daily の日付 {d.date} が start_date〜end_date の範囲外です",
            )


def _deactivate_label(db: Session, testing_id: int, label: str | None) -> None:
    """同 (testing_id, label) の全 is_active を False にする。"""
    db.execute(
        update(Plan)
        .where(Plan.testing_id == testing_id, _label_filter(label), Plan.is_active.is_(True))
        .values(is_active=False)
    )


def _label_exists(db: Session, testing_id: int, label: str) -> bool:
    queries = [
        select(PlanLabel.id).where(PlanLabel.testing_id == testing_id, PlanLabel.label == label),
        select(Plan.id).where(Plan.testing_id == testing_id, Plan.label == label),
        select(FileProgress.id).where(FileProgress.testing_id == testing_id, FileProgress.label == label),
        select(DailyProgress.id).where(DailyProgress.testing_id == testing_id, DailyProgress.label == label),
        select(DailyPersonProgress.id).where(
            DailyPersonProgress.testing_id == testing_id,
            DailyPersonProgress.label == label,
        ),
        select(TestResultBugSnapshot.id).where(
            TestResultBugSnapshot.testing_id == testing_id,
            TestResultBugSnapshot.label == label,
        ),
    ]
    return any(db.scalar(query) is not None for query in queries)


def _project_label_exists(db: Session, testing_id: int, label: str) -> bool:
    return _label_exists(db, testing_id, label)


def _apply_plan_label_payload(label: PlanLabel, payload: PlanLabelCreate) -> None:
    label.source_url = payload.source_url
    label.target_sheets = payload.target_sheets
    label.ignore_sheets = payload.ignore_sheets
    label.include_hidden_sheets = payload.include_hidden_sheets
    label.target_environments = payload.target_environments
    label.ignore_environments = payload.ignore_environments


# ---------- public API ----------

def list_plans(db: Session, testing_id: int) -> list[PlanItem]:
    _require_project(db, testing_id)
    plans = list(
        db.scalars(
            select(Plan)
            .where(Plan.testing_id == testing_id)
            .order_by(Plan.label.nullsfirst(), Plan.version.desc())
        )
    )
    totals = dict(
        db.execute(
            select(PlanDaily.plan_id, func.sum(PlanDaily.planned_count))
            .where(PlanDaily.plan_id.in_([p.id for p in plans]))
            .group_by(PlanDaily.plan_id)
        ).all()
    ) if plans else {}
    return [_to_item(p, totals.get(p.id, 0)) for p in plans]


def list_plan_labels(db: Session, testing_id: int) -> list[PlanLabelItem]:
    _require_project(db, testing_id)
    labels = list(
        db.scalars(
            select(PlanLabel)
            .where(PlanLabel.testing_id == testing_id)
            .order_by(PlanLabel.label)
        )
    )
    return [PlanLabelItem.model_validate(label) for label in labels]


def create_plan_label(db: Session, testing_id: int, payload: PlanLabelCreate) -> PlanLabelItem:
    _require_project(db, testing_id)
    existing = db.scalar(
        select(PlanLabel).where(
            PlanLabel.testing_id == testing_id,
            PlanLabel.label == payload.label,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="label already exists")

    label = PlanLabel(
        testing_id=testing_id,
        label=payload.label,
        source_url=payload.source_url,
        target_sheets=payload.target_sheets,
        ignore_sheets=payload.ignore_sheets,
        include_hidden_sheets=payload.include_hidden_sheets,
        target_environments=payload.target_environments,
        ignore_environments=payload.ignore_environments,
    )
    db.add(label)
    db.commit()
    db.refresh(label)
    return PlanLabelItem.model_validate(label)


def update_project_label(db: Session, testing_id: int, payload: ProjectLabelUpdate) -> PlanLabelItem:
    _require_project(db, testing_id)
    if not payload.old_label:
        existing = db.scalar(
            select(PlanLabel).where(PlanLabel.testing_id == testing_id, PlanLabel.label == payload.label)
        )
        if existing is not None:
            _apply_plan_label_payload(existing, payload)
            db.commit()
            db.refresh(existing)
            return PlanLabelItem.model_validate(existing)
        return create_plan_label(db, testing_id, PlanLabelCreate(**payload.model_dump(exclude={"old_label"})))

    if payload.old_label == payload.label:
        existing = db.scalar(
            select(PlanLabel).where(PlanLabel.testing_id == testing_id, PlanLabel.label == payload.label)
        )
        if existing is not None:
            _apply_plan_label_payload(existing, payload)
            db.commit()
            db.refresh(existing)
            return PlanLabelItem.model_validate(existing)
        return create_plan_label(db, testing_id, PlanLabelCreate(label=payload.label, source_url=payload.source_url))

    if not _project_label_exists(db, testing_id, payload.old_label):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="label not found")
    if _label_exists(db, testing_id, payload.label):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="label already exists")

    label = db.scalar(
        select(PlanLabel).where(PlanLabel.testing_id == testing_id, PlanLabel.label == payload.old_label)
    )
    if label is None:
        label = PlanLabel(
            testing_id=testing_id,
            label=payload.label,
            source_url=payload.source_url,
            target_sheets=payload.target_sheets,
            ignore_sheets=payload.ignore_sheets,
            include_hidden_sheets=payload.include_hidden_sheets,
            target_environments=payload.target_environments,
            ignore_environments=payload.ignore_environments,
        )
        db.add(label)
        db.flush()
    else:
        label.label = payload.label
        _apply_plan_label_payload(label, payload)

    for model in (Plan, FileProgress, DailyProgress, DailyPersonProgress, TestResultBugSnapshot):
        db.execute(
            update(model)
            .where(model.testing_id == testing_id, model.label == payload.old_label)
            .values(label=payload.label)
        )
    db.commit()
    db.refresh(label)
    return PlanLabelItem.model_validate(label)


def update_plan_label(db: Session, label_id: int, payload: PlanLabelUpdate) -> PlanLabelItem:
    label = _require_plan_label(db, label_id)
    return update_project_label(
        db,
        label.testing_id,
        ProjectLabelUpdate(old_label=label.label, label=payload.label, source_url=payload.source_url),
    )


def delete_project_label(db: Session, testing_id: int, label: str) -> None:
    _require_project(db, testing_id)
    if not _project_label_exists(db, testing_id, label):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="label not found")

    db.execute(delete(PlanLabel).where(PlanLabel.testing_id == testing_id, PlanLabel.label == label))
    db.execute(delete(Plan).where(Plan.testing_id == testing_id, Plan.label == label))
    db.execute(delete(FileProgress).where(FileProgress.testing_id == testing_id, FileProgress.label == label))
    db.execute(delete(DailyProgress).where(DailyProgress.testing_id == testing_id, DailyProgress.label == label))
    db.execute(delete(DailyPersonProgress).where(DailyPersonProgress.testing_id == testing_id, DailyPersonProgress.label == label))
    db.execute(delete(TestResultBugSnapshot).where(TestResultBugSnapshot.testing_id == testing_id, TestResultBugSnapshot.label == label))
    db.commit()


def delete_plan_label(db: Session, label_id: int) -> None:
    label = _require_plan_label(db, label_id)
    delete_project_label(db, label.testing_id, label.label)


def get_plan_detail(db: Session, plan_id: int) -> PlanDetail:
    plan = _require_plan(db, plan_id)
    daily_rows = list(
        db.scalars(select(PlanDaily).where(PlanDaily.plan_id == plan_id).order_by(PlanDaily.date))
    )
    daily_total = sum(r.planned_count for r in daily_rows)
    item = _to_item(plan, daily_total)
    return PlanDetail(
        **item.model_dump(),
        daily=[PlanDailyItem(date=r.date, planned_count=r.planned_count) for r in daily_rows],
    )


def create_plan(db: Session, testing_id: int, payload: PlanCreate) -> PlanDetail:
    _require_project(db, testing_id)
    _validate_daily(payload)

    max_version = db.scalar(
        select(func.max(Plan.version))
        .where(Plan.testing_id == testing_id, _label_filter(payload.label))
    )
    next_version = (max_version or 0) + 1

    if payload.activate:
        _deactivate_label(db, testing_id, payload.label)

    plan = Plan(
        testing_id=testing_id,
        label=payload.label,
        version=next_version,
        is_active=payload.activate,
        reason=payload.reason,
        planned_total_cases=payload.planned_total_cases,
        start_date=payload.start_date,
        end_date=payload.end_date,
        created_by=payload.created_by,
    )
    db.add(plan)
    db.flush()  # plan.id を確定

    daily_rows = [
        PlanDaily(plan_id=plan.id, date=d.date, planned_count=d.planned_count)
        for d in payload.daily
    ]
    db.add_all(daily_rows)
    db.commit()

    return get_plan_detail(db, plan.id)


def activate_plan(db: Session, plan_id: int) -> PlanItem:
    plan = _require_plan(db, plan_id)
    _deactivate_label(db, plan.testing_id, plan.label)
    plan.is_active = True
    db.commit()
    return _to_item(plan, _daily_total(db, plan_id))


def delete_plan(db: Session, plan_id: int) -> None:
    plan = _require_plan(db, plan_id)
    db.delete(plan)
    db.commit()

