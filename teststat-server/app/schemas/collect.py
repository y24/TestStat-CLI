from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CollectFailure(BaseModel):
    testing_id: int
    reason: str
    message: str


class CollectResult(BaseModel):
    targets: int
    succeeded: list[int]
    failed: list[CollectFailure]
    auth_error: bool
    started_at: datetime
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectStarted(BaseModel):
    started: bool
    targets: int
