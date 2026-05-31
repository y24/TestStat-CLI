import os
import sys
import unittest
from datetime import date
from unittest.mock import patch

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: F401
from app.crud.holiday import list_holidays, sync_holidays_from_cao, upsert_holiday  # noqa: E402
from app.database import Base  # noqa: E402
from app.schemas.holiday import HolidayCreate  # noqa: E402


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return Session()


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


class TestHolidayCRUD(unittest.TestCase):
    def setUp(self):
        self.db = make_session()

    def tearDown(self):
        self.db.close()

    def test_sync_adds_and_overwrites_holidays(self):
        first_csv = "国民の祝日・休日月日,国民の祝日・休日名称\n2026/1/1,元日\n2024/1/1,元日\n".encode("cp932")
        second_csv = (
            "国民の祝日・休日月日,国民の祝日・休日名称\n"
            "2026/1/1,元日更新\n"
            "2026/1/12,成人の日\n"
        ).encode("cp932")

        with patch("app.crud.holiday.urlopen", return_value=FakeResponse(first_csv)):
            first = sync_holidays_from_cao(self.db)
        self.assertEqual(first.updated, 1)

        with patch("app.crud.holiday.urlopen", return_value=FakeResponse(second_csv)):
            second = sync_holidays_from_cao(self.db)

        holidays = list_holidays(self.db)
        self.assertEqual(second.updated, 2)
        self.assertEqual(len(holidays), 2)
        self.assertEqual(holidays[0].date, date(2026, 1, 1))
        self.assertEqual(holidays[0].name, "元日更新")
        self.assertEqual(holidays[1].name, "成人の日")

    def test_upsert_holiday_adds_and_overwrites(self):
        created = upsert_holiday(self.db, HolidayCreate(date=date(2026, 6, 10), name="  独自休日  "))
        self.assertEqual(created.name, "独自休日")

        updated = upsert_holiday(self.db, HolidayCreate(date=date(2026, 6, 10), name="会社休日"))
        holidays = list_holidays(self.db)

        self.assertEqual(updated.name, "会社休日")
        self.assertEqual(len(holidays), 1)
        self.assertEqual(holidays[0].name, "会社休日")

    def test_upsert_holiday_before_2025_raises(self):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            upsert_holiday(self.db, HolidayCreate(date=date(2024, 12, 31), name="対象外"))
        self.assertEqual(ctx.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
