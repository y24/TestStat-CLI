from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class HolidayItem(BaseModel):
    date: date
    name: str

    model_config = ConfigDict(from_attributes=True)


class HolidayCreate(BaseModel):
    date: date
    name: str = Field(..., min_length=1, max_length=255)


class HolidaySyncResult(BaseModel):
    updated: int
    holidays: list[HolidayItem]
