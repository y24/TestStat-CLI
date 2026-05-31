from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    testing_id: int = Field(..., description="外部チケット管理システムのチケットID")
    name: str = Field(..., min_length=1, max_length=255)
    ticket_ref: str | None = Field(None, max_length=500)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    ticket_ref: str | None = Field(None, max_length=500)
    archived: bool | None = None


class ProjectResponse(BaseModel):
    testing_id: int
    name: str
    ticket_ref: str | None
    archived: bool
    created_at: datetime
    updated_at: datetime
    # 実績の有無（testings テーブルを参照）
    has_actuals: bool
    actuals_updated_at: datetime | None
    actual_available_cases: int
    actual_completed: int
    actual_completed_rate: float
    actual_all_completed: bool
    # 有効な計画バージョン数（Phase B2 で埋まる。現状は常に 0）
    active_plan_count: int

    model_config = ConfigDict(from_attributes=True)
