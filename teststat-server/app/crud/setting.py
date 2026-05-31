from sqlalchemy.orm import Session

from app.models.setting import ProgressStatusSetting
from app.schemas.setting import ProgressStatusThresholds

PROGRESS_STATUS_SETTING_ID = 1
DEFAULT_PROGRESS_STATUS_THRESHOLDS = ProgressStatusThresholds(caution=90, warning=60)


def get_progress_status_thresholds(db: Session) -> ProgressStatusThresholds:
    setting = db.get(ProgressStatusSetting, PROGRESS_STATUS_SETTING_ID)
    if not setting:
        return DEFAULT_PROGRESS_STATUS_THRESHOLDS
    return _to_schema(setting)


def update_progress_status_thresholds(
    db: Session,
    payload: ProgressStatusThresholds,
) -> ProgressStatusThresholds:
    setting = db.get(ProgressStatusSetting, PROGRESS_STATUS_SETTING_ID)
    if not setting:
        setting = ProgressStatusSetting(id=PROGRESS_STATUS_SETTING_ID)
        db.add(setting)

    setting.caution_threshold = payload.caution
    setting.warning_threshold = payload.warning
    db.commit()
    db.refresh(setting)
    return _to_schema(setting)


def _to_schema(setting: ProgressStatusSetting) -> ProgressStatusThresholds:
    return ProgressStatusThresholds(
        caution=setting.caution_threshold,
        warning=setting.warning_threshold,
    )
