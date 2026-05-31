import os
import sys
import unittest
from datetime import date

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine, event, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: F401  — 全モデルを Base.metadata に登録
from app.crud.plan import activate_plan, create_plan, delete_plan, get_plan_detail, list_plans  # noqa: E402
from app.crud.project import create_project  # noqa: E402
from app.database import Base  # noqa: E402
from app.schemas.plan import PlanCreate, PlanDailyIn  # noqa: E402
from app.schemas.project import ProjectCreate  # noqa: E402


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})

    # SQLite は接続ごとに FK を有効化する必要がある（CASCADE のため）
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return Session()


def make_daily(start: date, end: date, count_per_day: int = 10) -> list[PlanDailyIn]:
    from datetime import timedelta
    result = []
    d = start
    while d <= end:
        result.append(PlanDailyIn(date=d, planned_count=count_per_day))
        d += timedelta(days=1)
    return result


START = date(2026, 5, 1)
END = date(2026, 5, 5)


class TestPlanCRUD(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        create_project(self.db, ProjectCreate(testing_id=1001, name="テストP"))

    def tearDown(self):
        self.db.close()

    def _make_plan(self, label="TEST001", total=100, activate=True, daily=None) -> PlanCreate:
        return PlanCreate(
            label=label,
            reason="初期計画",
            planned_total_cases=total,
            start_date=START,
            end_date=END,
            activate=activate,
            daily=daily or make_daily(START, END),
        )

    # ---- 基本 CRUD ----

    def test_create_and_list(self):
        create_plan(self.db, 1001, self._make_plan("TEST001"))
        create_plan(self.db, 1001, self._make_plan("TEST002"))
        plans = list_plans(self.db, 1001)
        self.assertEqual(len(plans), 2)
        labels = {p.label for p in plans}
        self.assertIn("TEST001", labels)
        self.assertIn("TEST002", labels)

    def test_create_returns_detail_with_daily(self):
        detail = create_plan(self.db, 1001, self._make_plan())
        self.assertEqual(len(detail.daily), 5)  # 5/1〜5/5
        self.assertEqual(detail.daily_total, 50)  # 10×5

    def test_version_increments(self):
        v1 = create_plan(self.db, 1001, self._make_plan(activate=False))
        v2 = create_plan(self.db, 1001, self._make_plan(activate=False))
        self.assertEqual(v1.version, 1)
        self.assertEqual(v2.version, 2)

    def test_activate_flag_on_create(self):
        create_plan(self.db, 1001, self._make_plan(activate=True))
        create_plan(self.db, 1001, self._make_plan(activate=True))  # v2 が active
        plans = list_plans(self.db, 1001)
        active = [p for p in plans if p.is_active]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].version, 2)

    def test_activate_plan(self):
        v1 = create_plan(self.db, 1001, self._make_plan(activate=True))
        v2 = create_plan(self.db, 1001, self._make_plan(activate=True))
        # v1 に戻す
        activated = activate_plan(self.db, v1.id)
        self.assertTrue(activated.is_active)
        plans = list_plans(self.db, 1001)
        active = [p for p in plans if p.is_active]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].id, v1.id)

    def test_get_plan_detail(self):
        plan = create_plan(self.db, 1001, self._make_plan())
        detail = get_plan_detail(self.db, plan.id)
        self.assertEqual(detail.id, plan.id)
        self.assertEqual(len(detail.daily), 5)

    def test_delete_plan_cascades_daily(self):
        from app.models.plan import PlanDaily
        from sqlalchemy import select
        plan = create_plan(self.db, 1001, self._make_plan())
        plan_id = plan.id
        delete_plan(self.db, plan_id)
        remaining = self.db.scalars(select(PlanDaily).where(PlanDaily.plan_id == plan_id)).all()
        self.assertEqual(len(remaining), 0)

    # ---- バリデーション ----

    def test_invalid_date_range_raises(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            PlanCreate(
                label="X", planned_total_cases=100,
                start_date=date(2026, 5, 10), end_date=date(2026, 5, 1),
                activate=True, daily=[],
            )

    def test_daily_date_out_of_range_raises(self):
        from fastapi import HTTPException
        payload = PlanCreate(
            label="X", planned_total_cases=100,
            start_date=START, end_date=END, activate=True,
            daily=[PlanDailyIn(date=date(2026, 6, 1), planned_count=10)],
        )
        with self.assertRaises(HTTPException) as ctx:
            create_plan(self.db, 1001, payload)
        self.assertEqual(ctx.exception.status_code, 422)

    def test_duplicate_dates_in_daily_raises(self):
        from fastapi import HTTPException
        payload = PlanCreate(
            label="X", planned_total_cases=100,
            start_date=START, end_date=END, activate=True,
            daily=[
                PlanDailyIn(date=START, planned_count=10),
                PlanDailyIn(date=START, planned_count=20),
            ],
        )
        with self.assertRaises(HTTPException) as ctx:
            create_plan(self.db, 1001, payload)
        self.assertEqual(ctx.exception.status_code, 422)

    # ---- label=None（プロジェクト全体計画）----

    def test_null_label_versioning(self):
        v1 = create_plan(self.db, 1001, self._make_plan(label=None, activate=True))
        v2 = create_plan(self.db, 1001, self._make_plan(label=None, activate=True))
        self.assertEqual(v1.version, 1)
        self.assertEqual(v2.version, 2)
        plans = list_plans(self.db, 1001)
        active = [p for p in plans if p.is_active and p.label is None]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].version, 2)

    # ---- project not found ----

    def test_list_plans_unknown_project_raises(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            list_plans(self.db, 9999)
        self.assertEqual(ctx.exception.status_code, 404)

    # ---- active_plan_count が project に反映される ----

    def test_project_active_plan_count(self):
        from app.crud.project import get_project
        create_plan(self.db, 1001, self._make_plan("TEST001", activate=True))
        create_plan(self.db, 1001, self._make_plan("TEST002", activate=True))
        p = get_project(self.db, 1001)
        self.assertEqual(p.active_plan_count, 2)


if __name__ == "__main__":
    unittest.main()
