from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlanLabelCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)
    source_url: str | None = Field(None, max_length=2048)

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


class PlanLabelUpdate(PlanLabelCreate):
    pass


class ProjectLabelUpdate(PlanLabelCreate):
    old_label: str = Field(..., min_length=1, max_length=255)

    @field_validator("old_label")
    @classmethod
    def normalize_old_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("old_label は必須です")
        return normalized


class PlanLabelItem(BaseModel):
    id: int
    testing_id: int
    label: str
    source_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


