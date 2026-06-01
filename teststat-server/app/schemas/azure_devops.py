from datetime import date

from pydantic import BaseModel


class WorkItemResponse(BaseModel):
    work_item_id: int
    name: str
    start_date: date | None
    end_date: date | None
