from __future__ import annotations

import threading

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas.collect import CollectResult, CollectStarted
from app.services import collector

router = APIRouter(prefix="/api/v1", tags=["collect"])
_collect_lock = threading.Lock()


def _run_collect_all() -> None:
    try:
        collector.collect_all_with_new_session()
    finally:
        _collect_lock.release()


def _run_collect_project(testing_id: int) -> None:
    try:
        collector.collect_project_with_new_session(testing_id)
    finally:
        _collect_lock.release()


def _begin_collect() -> None:
    settings = get_settings()
    if not settings.collect_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="collector disabled")
    if not _collect_lock.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="collector already running")


@router.post("/collect", response_model=CollectStarted, status_code=status.HTTP_202_ACCEPTED)
def post_collect(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> CollectStarted:
    targets = collector.count_collect_targets(db)
    _begin_collect()
    background_tasks.add_task(_run_collect_all)
    return CollectStarted(started=True, targets=targets)


@router.post("/projects/{testing_id}/collect", response_model=CollectStarted, status_code=status.HTTP_202_ACCEPTED)
def post_project_collect(
    testing_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> CollectStarted:
    targets = collector.count_collect_targets(db, testing_id=testing_id)
    _begin_collect()
    background_tasks.add_task(_run_collect_project, testing_id)
    return CollectStarted(started=True, targets=targets)


@router.get("/collect/status", response_model=CollectResult | None)
def get_collect_status() -> CollectResult | None:
    return collector.get_last_result()
