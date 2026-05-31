from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
