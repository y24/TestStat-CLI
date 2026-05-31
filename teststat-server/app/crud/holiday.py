import csv
from datetime import date
from io import StringIO
from urllib.request import urlopen

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.holiday import Holiday
from app.schemas.holiday import HolidayCreate, HolidayItem, HolidaySyncResult

CAO_HOLIDAY_CSV_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
HOLIDAY_START_YEAR = 2025


def list_holidays(db: Session) -> list[HolidayItem]:
    holidays = list(db.scalars(select(Holiday).order_by(Holiday.date)))
    return [HolidayItem.model_validate(holiday) for holiday in holidays]


def upsert_holiday(db: Session, payload: HolidayCreate) -> HolidayItem:
    if payload.date.year < HOLIDAY_START_YEAR:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"祝日は {HOLIDAY_START_YEAR} 年以降の日付で登録してください",
        )

    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="祝日名を入力してください",
        )

    holiday = db.get(Holiday, payload.date)
    if holiday:
        holiday.name = name
    else:
        holiday = Holiday(date=payload.date, name=name)
        db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return HolidayItem.model_validate(holiday)


def sync_holidays_from_cao(db: Session) -> HolidaySyncResult:
    rows = _fetch_cao_holidays()
    db.execute(delete(Holiday).where(Holiday.date < date(HOLIDAY_START_YEAR, 1, 1)))
    for holiday_date, name in rows:
        existing = db.get(Holiday, holiday_date)
        if existing:
            existing.name = name
        else:
            db.add(Holiday(date=holiday_date, name=name))
    db.commit()
    return HolidaySyncResult(updated=len(rows), holidays=list_holidays(db))


def _fetch_cao_holidays() -> list[tuple[date, str]]:
    try:
        with urlopen(CAO_HOLIDAY_CSV_URL, timeout=20) as response:
            body = response.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"内閣府の祝日一覧を取得できませんでした: {exc}",
        ) from exc

    text = _decode_csv(body)
    reader = csv.reader(StringIO(text))
    rows: list[tuple[date, str]] = []
    for index, row in enumerate(reader):
        if index == 0 or len(row) < 2:
            continue
        raw_date = row[0].strip()
        name = row[1].strip()
        if not raw_date or not name:
            continue
        holiday_date = _parse_cao_date(raw_date)
        if holiday_date.year >= HOLIDAY_START_YEAR:
            rows.append((holiday_date, name))

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="内閣府の祝日一覧に有効な行がありませんでした",
        )
    return rows


def _decode_csv(body: bytes) -> str:
    for encoding in ("utf-8-sig", "cp932"):
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def _parse_cao_date(value: str) -> date:
    normalized = value.replace("/", "-")
    parts = normalized.split("-")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"内閣府の祝日日付を解析できませんでした: {value}",
        )
    try:
        year, month, day = (int(part) for part in parts)
        return date(year, month, day)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"内閣府の祝日日付を解析できませんでした: {value}",
        ) from exc
