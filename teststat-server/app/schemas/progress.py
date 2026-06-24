from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResultCounts(BaseModel):
    pass_count: int = Field(0, alias="Pass", ge=0)
    fixed: int = Field(0, alias="Fixed", ge=0)
    fail: int = Field(0, alias="Fail", ge=0)
    blocked: int = Field(0, alias="Blocked", ge=0)
    suspend: int = Field(0, alias="Suspend", ge=0)
    na: int = Field(0, alias="N/A", ge=0)

    model_config = ConfigDict(populate_by_name=True)


class DailyProgressIn(ResultCounts):
    date: date
    completed: int = Field(0, ge=0)
    executed: int = Field(0, ge=0)
    planned: int | None = Field(None, ge=0)


class PersonProgressIn(BaseModel):
    date: date
    person: str = Field(..., min_length=1, max_length=255)
    count: int = Field(..., ge=0)


class FileProgressIn(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    label: str | None = Field(None, max_length=255)
    source_url: str | None = Field(None, max_length=2048)
    subtask_id: int | None = Field(None, ge=0)
    target_sheets: list[str] | None = None
    ignore_sheets: list[str] | None = None
    include_hidden_sheets: bool | None = None
    target_environments: list[str] | None = None
    ignore_environments: list[str] | None = None
    environment: str | None = Field(None, max_length=255)
    total_cases: int = Field(..., ge=0)
    available_cases: int = Field(..., ge=0)
    excluded_cases: int = Field(..., ge=0)
    completed: int = Field(..., ge=0)
    executed: int = Field(..., ge=0)
    not_run: int = Field(..., ge=0)
    completed_rate: float = Field(..., ge=0)
    executed_rate: float = Field(..., ge=0)
    start_date: date | None = None
    latest_update: date | None = None
    results: ResultCounts = Field(default_factory=ResultCounts)
    daily: list[DailyProgressIn] = Field(default_factory=list)
    by_person: list[PersonProgressIn] = Field(default_factory=list)
    error: str | None = None

    @field_validator("source_url")
    @classmethod
    def normalize_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            raise ValueError("source_url must start with http:// or https://")
        return normalized

    @field_validator("target_sheets", "ignore_sheets", "target_environments", "ignore_environments")
    @classmethod
    def normalize_keyword_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("list items must be strings")
            text = item.strip()
            if text:
                normalized.append(text)
        return normalized


class ProgressRequest(BaseModel):
    testing_id: int = Field(..., description="YAML project.testing_id")
    project_name: str = Field(..., min_length=1, max_length=255)
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    files: list[FileProgressIn]


class ProgressPostResponse(BaseModel):
    testing_id: int
    inserted_files: int
    inserted_daily_rows: int
    inserted_person_rows: int


class SummaryCounts(BaseModel):
    total_cases: int
    available_cases: int
    completed: int
    executed: int
    completed_rate: float
    executed_rate: float


class ProgressSummaryResponse(BaseModel):
    testing_id: int
    project_name: str
    updated_at: datetime
    summary: SummaryCounts
    results: ResultCounts

    model_config = ConfigDict(from_attributes=True)


class FileProgressItem(BaseModel):
    file_name: str
    label: str | None
    environment: str | None
    total_cases: int
    available_cases: int
    completed: int
    executed: int
    completed_rate: float
    executed_rate: float
    start_date: date | None
    latest_update: date | None
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyProgressItem(ResultCounts):
    date: date
    file_name: str
    label: str | None
    environment: str | None
    completed: int
    executed: int
    planned: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TestingItem(BaseModel):
    testing_id: int
    project_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
