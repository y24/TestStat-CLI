from sqlalchemy.orm import Session

from app.models.setting import PbChartSetting, ProgressStatusSetting
from app.schemas.setting import PbChartSettings, ProgressStatusThresholds

PROGRESS_STATUS_SETTING_ID = 1
PB_CHART_SETTING_ID = 1
DEFAULT_PROGRESS_STATUS_THRESHOLDS = ProgressStatusThresholds(caution=90, warning=60)
DEFAULT_PB_CHART_SETTINGS = PbChartSettings(bug_axis_max=30)


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


def get_pb_chart_settings(db: Session) -> PbChartSettings:
    setting = db.get(PbChartSetting, PB_CHART_SETTING_ID)
    if not setting:
        return DEFAULT_PB_CHART_SETTINGS
    return _pb_chart_to_schema(setting)


def update_pb_chart_settings(
    db: Session,
    payload: PbChartSettings,
) -> PbChartSettings:
    setting = db.get(PbChartSetting, PB_CHART_SETTING_ID)
    if not setting:
        setting = PbChartSetting(id=PB_CHART_SETTING_ID)
        db.add(setting)

    setting.bug_axis_max = payload.bug_axis_max
    db.commit()
    db.refresh(setting)
    return _pb_chart_to_schema(setting)


def _pb_chart_to_schema(setting: PbChartSetting) -> PbChartSettings:
    return PbChartSettings(bug_axis_max=setting.bug_axis_max)

