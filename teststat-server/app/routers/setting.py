from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud.setting import (
    get_bug_state_color_settings,
    get_pb_chart_settings,
    get_progress_status_thresholds,
    update_bug_state_color_settings,
    update_pb_chart_settings,
    update_progress_status_thresholds,
)
from app.database import get_db
from app.schemas.setting import BugStateColorSettings, PbChartSettings, ProgressStatusThresholds

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("/progress-status-thresholds", response_model=ProgressStatusThresholds)
def read_progress_status_thresholds(db: Session = Depends(get_db)) -> ProgressStatusThresholds:
    return get_progress_status_thresholds(db)


@router.patch("/progress-status-thresholds", response_model=ProgressStatusThresholds)
def patch_progress_status_thresholds(
    payload: ProgressStatusThresholds,
    db: Session = Depends(get_db),
) -> ProgressStatusThresholds:
    return update_progress_status_thresholds(db, payload)


@router.get("/pb-chart", response_model=PbChartSettings)
def read_pb_chart_settings(db: Session = Depends(get_db)) -> PbChartSettings:
    return get_pb_chart_settings(db)


@router.patch("/pb-chart", response_model=PbChartSettings)
def patch_pb_chart_settings(
    payload: PbChartSettings,
    db: Session = Depends(get_db),
) -> PbChartSettings:
    return update_pb_chart_settings(db, payload)


@router.get("/bug-state-colors", response_model=BugStateColorSettings)
def read_bug_state_color_settings(db: Session = Depends(get_db)) -> BugStateColorSettings:
    return get_bug_state_color_settings(db)


@router.patch("/bug-state-colors", response_model=BugStateColorSettings)
def patch_bug_state_color_settings(
    payload: BugStateColorSettings,
    db: Session = Depends(get_db),
) -> BugStateColorSettings:
    return update_bug_state_color_settings(db, payload)

