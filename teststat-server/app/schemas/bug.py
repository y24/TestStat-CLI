from datetime import datetime

from pydantic import BaseModel


class BugSyncResponse(BaseModel):
    testing_id: int
    fetched: int            # 洗替後の総件数（IGNORE 除外後・Suspend 含む）
    open_count: int         # うち未解消（赤）
    suspended_count: int    # うち対応見送り（黄）
    resolved_count: int     # うち完了（緑）
    fetched_at: datetime


class OpenBugItem(BaseModel):
    work_item_id: int
    title: str | None
    state: str | None
    url: str | None
