from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud.setting import get_progress_status_thresholds, update_progress_status_thresholds
from app.database import get_db
from app.schemas.setting import ProgressStatusThresholds

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
