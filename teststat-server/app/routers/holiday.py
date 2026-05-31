from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud.holiday import list_holidays, sync_holidays_from_cao, upsert_holiday
from app.database import get_db
from app.schemas.holiday import HolidayCreate, HolidayItem, HolidaySyncResult

router = APIRouter(prefix="/api/v1", tags=["holidays"])


@router.get("/holidays", response_model=list[HolidayItem])
def read_holidays(db: Session = Depends(get_db)) -> list[HolidayItem]:
    return list_holidays(db)


@router.post("/holidays", response_model=HolidayItem)
def post_holiday(payload: HolidayCreate, db: Session = Depends(get_db)) -> HolidayItem:
    return upsert_holiday(db, payload)


@router.post("/holidays/sync", response_model=HolidaySyncResult)
def post_holiday_sync(db: Session = Depends(get_db)) -> HolidaySyncResult:
    return sync_holidays_from_cao(db)
