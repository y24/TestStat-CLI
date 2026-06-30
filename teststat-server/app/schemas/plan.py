from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlanLabelCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)
    is_disabled: bool = False
    source_url: str | None = Field(None, max_length=2048)
    use_plan_as_actual_offset: bool = True
    subtask_id: int | None = Field(None, ge=0)
    target_sheets: list[str] | None = None
    ignore_sheets: list[str] | None = None
    include_hidden_sheets: bool | None = None
    target_environments: list[str] | None = None
    ignore_environments: list[str] | None = None

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("label は必須です")
        return normalized
    @field_validator("source_url")
    @classmethod
    def normalize_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            raise ValueError("source_url は http:// または https:// で始まる必要があります")
        return normalized

    @field_validator("target_sheets", "ignore_sheets", "target_environments", "ignore_environments")
    @classmethod
    def normalize_keyword_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("リスト項目は文字列で指定してください")
            text = item.strip()
            if text:
                normalized.append(text)
        return normalized or None


class PlanLabelUpdate(PlanLabelCreate):
    pass


class ProjectLabelUpdate(PlanLabelCreate):
    old_label: str = Field("", max_length=255)

    @field_validator("old_label")
    @classmethod
    def normalize_old_label(cls, value: str) -> str:
        return value.strip()


class PlanLabelItem(BaseModel):
    id: int
    testing_id: int
    label: str
    is_disabled: bool
    source_url: str | None
    subtask_id: int | None
    use_plan_as_actual_offset: bool
    target_sheets: list[str] | None
    ignore_sheets: list[str] | None
    include_hidden_sheets: bool | None
    target_environments: list[str] | None
    ignore_environments: list[str] | None
    display_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlanLabelOrderUpdate(BaseModel):
    label_ids: list[int] | None = Field(None, min_length=1)
    labels: list[str] | None = Field(None, min_length=1)

    @field_validator("labels")
    @classmethod
    def normalize_labels(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [label.strip() for label in value if label.strip()]
        if not normalized:
            raise ValueError("labels は1件以上必要です")
        return normalized

    @model_validator(mode="after")
    def require_order_target(self) -> "PlanLabelOrderUpdate":
        if self.label_ids is None and self.labels is None:
            raise ValueError("label_ids または labels が必要です")
        return self


class PlanDailyIn(BaseModel):
    date: date
    planned_count: int = Field(..., ge=0)


class PlanCreate(BaseModel):
    label: str | None = Field(None, max_length=255)
    reason: str | None = Field(None, max_length=500)
    planned_total_cases: int = Field(..., ge=1)
    start_date: date
    end_date: date
    activate: bool = True
    daily: list[PlanDailyIn] = Field(default_factory=list)
    created_by: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def check_dates(self) -> "PlanCreate":
        if self.start_date > self.end_date:
            raise ValueError("start_date は end_date 以前である必要があります")
        return self


class PlanDailyItem(BaseModel):
    date: date
    planned_count: int

    model_config = ConfigDict(from_attributes=True)


class PlanItem(BaseModel):
    id: int
    testing_id: int
    label: str | None
    version: int
    is_active: bool
    reason: str | None
    planned_total_cases: int
    start_date: date
    end_date: date
    created_at: datetime
    created_by: str | None
    daily_total: int  # plan_daily の planned_count 合計

    model_config = ConfigDict(from_attributes=True)


class PlanDetail(PlanItem):
    daily: list[PlanDailyItem]


