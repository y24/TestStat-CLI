from sqlalchemy.orm import Session

from app.models.setting import BugStateColorSetting, PbChartSetting, ProgressStatusSetting
from app.schemas.setting import (
    BugStateColorSetting as BugStateColorSettingSchema,
    BugStateColorSettings,
    PbChartSettings,
    ProgressStatusThresholds,
)

PROGRESS_STATUS_SETTING_ID = 1
PB_CHART_SETTING_ID = 1
DEFAULT_PROGRESS_STATUS_THRESHOLDS = ProgressStatusThresholds(caution=90, warning=60)
DEFAULT_PB_CHART_SETTINGS = PbChartSettings(bug_axis_max=30)

DEFAULT_BUG_STATE_COLORS = BugStateColorSettings(
    items=[
        BugStateColorSettingSchema(
            state="New",
            background_color="#f7f9fb",
            text_color="#5f6b7a",
            border_color="#d8dee8",
        ),
        BugStateColorSettingSchema(
            state="In Progress",
            background_color="#eef9ff",
            text_color="#0369a1",
            border_color="#bae6fd",
        ),
        BugStateColorSettingSchema(
            state="Dev In Progress",
            background_color="#f5f0ff",
            text_color="#6b46c1",
            border_color="#ddd0ff",
        ),
        BugStateColorSettingSchema(
            state="Resolved",
            background_color="#e9d5ff",
            text_color="#581c87",
            border_color="#c084fc",
        ),
        BugStateColorSettingSchema(
            state="Done",
            background_color="#edf8f3",
            text_color="#147d54",
            border_color="#bfdacb",
        ),
        BugStateColorSettingSchema(
            state="Suspend",
            background_color="#fff8e6",
            text_color="#8a5a00",
            border_color="#f5d58a",
        ),
    ]
)


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


def get_bug_state_color_settings(db: Session) -> BugStateColorSettings:
    settings = (
        db.query(BugStateColorSetting)
        .order_by(BugStateColorSetting.display_order, BugStateColorSetting.id)
        .all()
    )
    if not settings:
        return DEFAULT_BUG_STATE_COLORS
    return BugStateColorSettings(items=[_bug_state_color_to_schema(setting) for setting in settings])


def update_bug_state_color_settings(
    db: Session,
    payload: BugStateColorSettings,
) -> BugStateColorSettings:
    db.query(BugStateColorSetting).delete()
    for index, item in enumerate(payload.items):
        db.add(
            BugStateColorSetting(
                state=item.state,
                background_color=item.background_color,
                text_color=item.text_color,
                border_color=item.border_color,
                display_order=index,
            )
        )
    db.commit()
    return get_bug_state_color_settings(db)


def _bug_state_color_to_schema(setting: BugStateColorSetting) -> BugStateColorSettingSchema:
    return BugStateColorSettingSchema(
        state=setting.state,
        background_color=setting.background_color,
        text_color=setting.text_color,
        border_color=setting.border_color,
    )

