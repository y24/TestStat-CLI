import os
import sys
import unittest
from datetime import date

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: F401
from app.crud.pb_chart import get_pb_chart  # noqa: E402
from app.crud.plan import create_plan  # noqa: E402
from app.crud.project import create_project  # noqa: E402
from app.database import Base  # noqa: E402
from app.schemas.plan import PlanCreate, PlanDailyIn  # noqa: E402
from app.schemas.project import ProjectCreate  # noqa: E402


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_fk(conn, _):
        conn.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _insert_actuals(db, testing_id: int, rows: list[tuple[str | None, date, int]]):
    """(label, date, executed) のリストを daily_progress へ直接挿入。"""
    from app.models.progress import DailyProgress, Testing
    # testings レコードが必要（FK）
    from sqlalchemy import select
    if not db.scalar(select(Testing).where(Testing.testing_id == testing_id)):
        db.add(Testing(testing_id=testing_id, project_name=f"P{testing_id}"))
        db.flush()
    for label, d, executed in rows:
        db.add(DailyProgress(
            testing_id=testing_id, file_name="f.xlsx",
            label=label, date=d,
            executed=executed, completed=executed,
            result_pass=executed, result_fixed=0, result_fail=0,
            result_blocked=0, result_suspend=0, result_na=0,
        ))
    db.commit()


def _insert_file_progress(db, testing_id: int, label: str | None, available: int):
    from app.models.progress import FileProgress, Testing
    from sqlalchemy import select
    from datetime import datetime
    if not db.scalar(select(Testing).where(Testing.testing_id == testing_id)):
        db.add(Testing(testing_id=testing_id, project_name=f"P{testing_id}"))
        db.flush()
    db.add(FileProgress(
        testing_id=testing_id, file_name="f.xlsx", label=label,
        total_cases=available, available_cases=available, excluded_cases=0,
        completed=0, executed=0, not_run=available,
        completed_rate=0.0, executed_rate=0.0,
        result_pass=0, result_fixed=0, result_fail=0,
        result_blocked=0, result_suspend=0, result_na=0,
        sent_at=datetime(2026, 5, 20, 18, 0),
    ))
    db.commit()


START = date(2026, 5, 1)
END = date(2026, 5, 5)  # 5日間


class TestPbChart(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        create_project(self.db, ProjectCreate(testing_id=1001, name="テストP"))

    def tearDown(self):
        self.db.close()

    def _make_plan(self, label="TEST001", total=100, daily_counts=None, activate=True):
        daily_counts = daily_counts or [20, 20, 20, 20, 20]  # 合計 100
        daily = [PlanDailyIn(date=date(2026, 5, i + 1), planned_count=c) for i, c in enumerate(daily_counts)]
        return create_plan(self.db, 1001, PlanCreate(
            label=label, planned_total_cases=total,
            start_date=START, end_date=END,
            activate=activate, daily=daily,
        ))

    # ---- 計画のみ（実績なし） ----

    def test_plan_only(self):
        self._make_plan(total=100, daily_counts=[20, 20, 20, 20, 20])
        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertEqual(result.planned_total_cases, 100)
        self.assertEqual(result.available_cases, 0)
        self.assertIsNotNone(result.range)
        self.assertEqual(len(result.series), 5)

        # 1日目: remaining = 100 - 20 = 80
        s0 = result.series[0]
        self.assertEqual(s0.planned_remaining, 80)
        self.assertEqual(s0.planned_completed_daily, 20)
        self.assertIsNone(s0.actual_remaining)
        self.assertIsNone(s0.actual_completed_daily)

        # 最終日: remaining = 0
        self.assertEqual(result.series[-1].planned_remaining, 0)

    # ---- 実績のみ（計画なし） ----

    def test_actuals_only(self):
        _insert_file_progress(self.db, 1001, "TEST001", available=100)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 25),
            ("TEST001", date(2026, 5, 3), 30),
        ])
        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertIsNone(result.planned_total_cases)
        self.assertEqual(result.available_cases, 100)
        self.assertEqual(result.range, {"from": "2026-05-01", "to": "2026-05-03"})

        # 5/1: actual_remaining = 100 - 25 = 75
        s0 = result.series[0]
        self.assertEqual(s0.actual_completed_daily, 25)
        self.assertEqual(s0.actual_remaining, 75)
        self.assertIsNone(s0.planned_remaining)

        # 5/2: actual がない日→前日値を引き継ぎ
        s1 = result.series[1]
        self.assertIsNone(s1.actual_completed_daily)
        self.assertEqual(s1.actual_remaining, 75)

        # 5/3: actual_remaining = 75 - 30 = 45
        s2 = result.series[2]
        self.assertEqual(s2.actual_remaining, 45)

    # ---- 計画＋実績 ----

    def test_plan_and_actuals(self):
        self._make_plan(total=100, daily_counts=[20] * 5)
        _insert_file_progress(self.db, 1001, "TEST001", available=100)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 15),  # 計画より少ない
            ("TEST001", date(2026, 5, 2), 25),  # 計画より多い
        ])
        result = get_pb_chart(self.db, 1001, label="TEST001")

        # range は plan_end まで広がる
        self.assertEqual(result.range["to"], "2026-05-05")

        s0 = result.series[0]
        self.assertEqual(s0.planned_remaining, 80)   # 100 - 20
        self.assertEqual(s0.actual_remaining, 85)    # 100 - 15
        self.assertEqual(s0.planned_completed_daily, 20)
        self.assertEqual(s0.actual_completed_daily, 15)

        s1 = result.series[1]
        self.assertEqual(s1.planned_remaining, 60)   # 100 - 20 - 20
        self.assertEqual(s1.actual_remaining, 60)    # 100 - 15 - 25

        # 実績データ最終日より後は actual_remaining = None
        s4 = result.series[4]  # 5/5
        self.assertIsNone(s4.actual_remaining)

    # ---- 全テスト合算（label=None） ----

    def test_all_labels_aggregated(self):
        self._make_plan(label="TEST001", total=100, daily_counts=[20] * 5)
        self._make_plan(label="TEST002", total=50, daily_counts=[10] * 5)
        _insert_file_progress(self.db, 1001, "TEST001", available=100)
        _insert_file_progress(self.db, 1001, "TEST002", available=50)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 10),
            ("TEST002", date(2026, 5, 1), 5),
        ])
        result = get_pb_chart(self.db, 1001, label=None)

        self.assertEqual(result.planned_total_cases, 150)   # 100 + 50
        self.assertEqual(result.available_cases, 150)       # 100 + 50

        s0 = result.series[0]
        self.assertEqual(s0.planned_completed_daily, 30)    # 20 + 10
        self.assertEqual(s0.planned_remaining, 120)         # 150 - 30
        self.assertEqual(s0.actual_completed_daily, 15)     # 10 + 5
        self.assertEqual(s0.actual_remaining, 135)          # 150 - 15

    # ---- 過去計画 ----

    def test_past_plans_returned(self):
        v1 = self._make_plan(total=80, daily_counts=[16] * 5, activate=True)
        v2 = self._make_plan(total=100, daily_counts=[20] * 5, activate=True)  # v1 が非有効に
        result = get_pb_chart(self.db, 1001, label="TEST001", include_past_plans=True)

        self.assertEqual(len(result.past_plans), 1)
        pp = result.past_plans[0]
        self.assertEqual(pp.version, 1)
        self.assertEqual(pp.planned_total_cases, 80)
        # 1日目: 80 - 16 = 64
        self.assertEqual(pp.series[0].planned_remaining, 64)

    def test_past_plans_aggregated_for_all_labels(self):
        self._make_plan(label="TEST001", total=100, daily_counts=[20] * 5, activate=True)
        self._make_plan(label="TEST002", total=50, daily_counts=[10] * 5, activate=True)
        self._make_plan(label="TEST001", total=125, daily_counts=[25] * 5, activate=True)
        self._make_plan(label="TEST002", total=75, daily_counts=[15] * 5, activate=True)

        result = get_pb_chart(self.db, 1001, label=None, include_past_plans=True)

        self.assertEqual(len(result.past_plans), 1)
        pp = result.past_plans[0]
        self.assertEqual(pp.version, 1)
        self.assertIsNone(pp.label)
        self.assertEqual(pp.planned_total_cases, 150)       # 100 + 50
        self.assertEqual(pp.series[0].planned_completed_daily, 30)  # 20 + 10
        self.assertEqual(pp.series[0].planned_remaining, 120)       # 150 - 30

    def test_past_plan_for_one_label_includes_other_active_labels_in_all_view(self):
        self._make_plan(label="TEST001", total=80, daily_counts=[16] * 5, activate=True)
        self._make_plan(label="TEST002", total=50, daily_counts=[10] * 5, activate=True)
        self._make_plan(label="TEST001", total=100, daily_counts=[20] * 5, activate=True)

        result = get_pb_chart(self.db, 1001, label=None, include_past_plans=True)

        self.assertEqual(len(result.past_plans), 1)
        pp = result.past_plans[0]
        self.assertEqual(pp.version, 1)
        self.assertIsNone(pp.label)
        self.assertEqual(pp.planned_total_cases, 130)       # TEST001 v1 + TEST002 active
        self.assertEqual(pp.series[0].planned_completed_daily, 26)  # 16 + 10
        self.assertEqual(pp.series[0].planned_remaining, 104)       # 130 - 26

    def test_past_plans_not_returned_by_default(self):
        self._make_plan(total=80, activate=True)
        self._make_plan(total=100, activate=True)
        result = get_pb_chart(self.db, 1001, label="TEST001")
        self.assertEqual(result.past_plans, [])

    # ---- データなし ----

    def test_no_data_returns_empty(self):
        result = get_pb_chart(self.db, 1001)
        self.assertIsNone(result.range)
        self.assertEqual(result.series, [])
        self.assertIsNone(result.planned_total_cases)
        self.assertEqual(result.available_cases, 0)

    def test_test_result_bug_source_uses_fail_suspend_fixed(self):
        from app.crud.project import update_project
        from app.models.progress import TestResultBugSnapshot, Testing
        from app.schemas.project import ProjectUpdate
        from datetime import datetime
        from sqlalchemy import select

        update_project(self.db, 1001, ProjectUpdate(bug_count_source="test_result"))
        if not self.db.scalar(select(Testing).where(Testing.testing_id == 1001)):
            self.db.add(Testing(testing_id=1001, project_name="P1001", updated_at=datetime(2026, 5, 3, 12, 0)))
            self.db.flush()
        self.db.add_all(
            [
                TestResultBugSnapshot(
                    testing_id=1001,
                    snapshot_date=date(2026, 5, 1),
                    fail_count=2,
                    suspend_count=1,
                    fixed_count=0,
                    sent_at=datetime(2026, 5, 1, 10, 0),
                ),
                TestResultBugSnapshot(
                    testing_id=1001,
                    snapshot_date=date(2026, 5, 3),
                    fail_count=1,
                    suspend_count=1,
                    fixed_count=2,
                    sent_at=datetime(2026, 5, 3, 10, 0),
                ),
            ]
        )
        self.db.commit()

        result = get_pb_chart(self.db, 1001)

        self.assertTrue(result.has_bugs)
        self.assertEqual(result.range, {"from": "2026-05-01", "to": "2026-05-03"})
        self.assertEqual(
            [(item.bug_open, item.bug_suspended, item.bug_resolved) for item in result.series],
            [(2, 1, 0), (2, 1, 0), (1, 1, 2)],
        )

    # ---- 存在しないプロジェクト ----

    def test_unknown_project_raises(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            get_pb_chart(self.db, 9999)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
