from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectCreate(BaseModel):
    testing_id: int = Field(..., description="外部チケット管理システムのチケットID")
    name: str = Field(..., min_length=1, max_length=255)
    ticket_ref: str | None = Field(None, max_length=500)
    planned_start_date: date | None = None
    planned_end_date: date | None = None

    @model_validator(mode="after")
    def validate_planned_date_range(self) -> "ProjectCreate":
        if (
            self.planned_start_date is not None
            and self.planned_end_date is not None
            and self.planned_start_date > self.planned_end_date
        ):
            raise ValueError("planned_start_date must be before or equal to planned_end_date")
        return self


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    ticket_ref: str | None = Field(None, max_length=500)
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def validate_planned_date_range(self) -> "ProjectUpdate":
        if (
            self.planned_start_date is not None
            and self.planned_end_date is not None
            and self.planned_start_date > self.planned_end_date
        ):
            raise ValueError("planned_start_date must be before or equal to planned_end_date")
        return self


class ProjectResponse(BaseModel):
    testing_id: int
    name: str
    ticket_ref: str | None
    planned_start_date: date | None
    planned_end_date: date | None
    archived: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
    # 実績の有無（testings テーブルを参照）
    has_actuals: bool
    actuals_updated_at: datetime | None
    actual_available_cases: int
    actual_completed: int
    actual_completed_rate: float
    actual_vs_plan_rate: float | None
    actual_all_completed: bool
    # 有効な計画バージョン数（Phase B2 で埋まる。現状は常に 0）
    active_plan_count: int

    model_config = ConfigDict(from_attributes=True)


class ProjectOrderUpdate(BaseModel):
    testing_ids: list[int] = Field(..., min_length=1)
