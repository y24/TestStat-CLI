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
from app.crud.plan import create_plan, create_plan_label  # noqa: E402
from app.crud.project import create_project  # noqa: E402
from app.database import Base  # noqa: E402
from app.schemas.plan import PlanCreate, PlanDailyIn, PlanLabelCreate  # noqa: E402
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


def _insert_file_progress(db, testing_id: int, label: str | None, available: int, executed: int = 0):
    from app.models.progress import FileProgress, Testing
    from sqlalchemy import select
    from datetime import datetime
    if not db.scalar(select(Testing).where(Testing.testing_id == testing_id)):
        db.add(Testing(testing_id=testing_id, project_name=f"P{testing_id}"))
        db.flush()
    db.add(FileProgress(
        testing_id=testing_id, file_name="f.xlsx", label=label,
        total_cases=available, available_cases=available, excluded_cases=0,
        completed=executed, executed=executed, not_run=max(available - executed, 0),
        completed_rate=round((executed / available) * 100, 2) if available else 0.0, executed_rate=round((executed / available) * 100, 2) if available else 0.0,
        result_pass=executed, result_fixed=0, result_fail=0,
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

    def _point_by_date(self, result, target_date):
        return next(point for point in result.series if point.date == target_date)

    # ---- 計画のみ（実績なし） ----

    def test_plan_only(self):
        self._make_plan(total=100, daily_counts=[20, 20, 20, 20, 20])
        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertEqual(result.planned_total_cases, 100)
        self.assertEqual(result.available_cases, 0)
        self.assertIsNotNone(result.range)
        self.assertEqual(len(result.series), 6)

        # 0日目: remaining = 100、1日目: remaining = 100 - 20 = 80
        s0 = self._point_by_date(result, date(2026, 4, 30))
        self.assertEqual(s0.planned_remaining, 100)
        self.assertEqual(s0.planned_completed_daily, 0)
        s1 = self._point_by_date(result, date(2026, 5, 1))
        self.assertEqual(s1.planned_remaining, 80)
        self.assertEqual(s1.planned_completed_daily, 20)
        self.assertEqual(s0.actual_remaining, 100)
        self.assertIsNone(s0.actual_completed_daily)

        # 最終日: planned remaining = 0, actual remaining is unknown because no actual data exists yet
        self.assertEqual(result.series[-1].planned_remaining, 0)
        self.assertIsNone(result.series[-1].actual_remaining)


    def test_plan_only_offset_can_be_disabled(self):
        self._make_plan(total=100, daily_counts=[20, 20, 20, 20, 20])
        create_plan_label(
            self.db,
            1001,
            PlanLabelCreate(label="TEST001", use_plan_as_actual_offset=False),
        )

        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertIsNone(self._point_by_date(result, date(2026, 4, 30)).actual_remaining)
        self.assertFalse(result.plan_case_mismatch)
    def test_disabled_plan_only_offset_is_excluded_from_completion_metrics(self):
        self._make_plan(label="TEST001", total=100, daily_counts=[20] * 5)
        self._make_plan(label="TEST002", total=50, daily_counts=[10] * 5)
        create_plan_label(
            self.db,
            1001,
            PlanLabelCreate(label="TEST002", use_plan_as_actual_offset=False),
        )
        _insert_file_progress(self.db, 1001, "TEST001", available=100, executed=10)
        _insert_actuals(self.db, 1001, [("TEST001", date(2026, 5, 1), 10)])

        result = get_pb_chart(self.db, 1001, label=None)

        self.assertEqual(result.actual_total_cases, 100)
        self.assertEqual(result.actual_executed_to_latest, 10)
        self.assertEqual(result.planned_completed_to_latest_actual, 20)
    # ---- 実績のみ（計画なし） ----

    def test_actuals_only(self):
        _insert_file_progress(self.db, 1001, "TEST001", available=100, executed=55)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 25),
            ("TEST001", date(2026, 5, 3), 30),
        ])
        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertIsNone(result.planned_total_cases)
        self.assertEqual(result.available_cases, 100)
        self.assertEqual(result.range, {"from": "2026-04-30", "to": "2026-05-03"})

        # 4/30: actual_remaining = 100、5/1: actual_remaining = 100 - 25 = 75
        s0 = self._point_by_date(result, date(2026, 4, 30))
        self.assertIsNone(s0.actual_completed_daily)
        self.assertEqual(s0.actual_remaining, 100)
        s1 = self._point_by_date(result, date(2026, 5, 1))
        self.assertEqual(s1.actual_completed_daily, 25)
        self.assertEqual(s1.actual_remaining, 75)
        self.assertIsNone(s0.planned_remaining)

        # 5/2: actual がない日→前日値を引き継ぎ
        s1 = self._point_by_date(result, date(2026, 5, 2))
        self.assertIsNone(s1.actual_completed_daily)
        self.assertEqual(s1.actual_remaining, 75)

        # 5/3: actual_remaining = 75 - 30 = 45
        s2 = self._point_by_date(result, date(2026, 5, 3))
        self.assertEqual(s2.actual_remaining, 45)

    def test_dated_rows_without_results_do_not_draw_actual_series(self):
        self._make_plan(total=100, daily_counts=[20] * 5)
        _insert_file_progress(self.db, 1001, "TEST001", available=100, executed=0)
        _insert_actuals(self.db, 1001, [("TEST001", date(2026, 5, 2), 0)])

        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertTrue(result.series)
        self.assertTrue(all(point.actual_remaining is None for point in result.series))
        self.assertTrue(all(point.actual_completed_daily is None for point in result.series))

    def test_zero_result_dates_do_not_extend_actual_series(self):
        self._make_plan(total=100, daily_counts=[20] * 5)
        _insert_file_progress(self.db, 1001, "TEST001", available=100, executed=10)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 10),
            ("TEST001", date(2026, 5, 4), 0),
        ])

        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertEqual(self._point_by_date(result, date(2026, 5, 1)).actual_remaining, 90)
        self.assertIsNone(self._point_by_date(result, date(2026, 5, 2)).actual_remaining)
        self.assertIsNone(self._point_by_date(result, date(2026, 5, 4)).actual_completed_daily)

    # ---- 計画＋実績 ----

    def test_plan_and_actuals(self):
        self._make_plan(total=100, daily_counts=[20] * 5)
        _insert_file_progress(self.db, 1001, "TEST001", available=100, executed=40)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 15),  # 計画より少ない
            ("TEST001", date(2026, 5, 2), 25),  # 計画より多い
        ])
        result = get_pb_chart(self.db, 1001, label="TEST001")

        # range は plan_end まで広がる
        self.assertEqual(result.range["to"], "2026-05-05")

        s0 = self._point_by_date(result, date(2026, 4, 30))
        self.assertEqual(s0.planned_remaining, 100)
        self.assertEqual(s0.actual_remaining, 100)
        self.assertEqual(s0.planned_completed_daily, 0)
        self.assertIsNone(s0.actual_completed_daily)

        s1 = self._point_by_date(result, date(2026, 5, 1))
        self.assertEqual(s1.planned_remaining, 80)   # 100 - 20
        self.assertEqual(s1.actual_remaining, 85)    # 100 - 15
        self.assertEqual(s1.planned_completed_daily, 20)
        self.assertEqual(s1.actual_completed_daily, 15)

        s1 = self._point_by_date(result, date(2026, 5, 2))
        self.assertEqual(s1.planned_remaining, 60)   # 100 - 20 - 20
        self.assertEqual(s1.actual_remaining, 60)    # 100 - 15 - 25

        # 実績データ最終日より後は actual_remaining = None
        s4 = self._point_by_date(result, date(2026, 5, 5))
        self.assertIsNone(s4.actual_remaining)

    # ---- 全テスト合算（label=None） ----

    def test_all_labels_aggregated(self):
        self._make_plan(label="TEST001", total=100, daily_counts=[20] * 5)
        self._make_plan(label="TEST002", total=50, daily_counts=[10] * 5)
        _insert_file_progress(self.db, 1001, "TEST001", available=100, executed=10)
        _insert_file_progress(self.db, 1001, "TEST002", available=50, executed=5)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 10),
            ("TEST002", date(2026, 5, 1), 5),
        ])
        result = get_pb_chart(self.db, 1001, label=None)

        self.assertEqual(result.planned_total_cases, 150)   # 100 + 50
        self.assertEqual(result.available_cases, 150)       # 100 + 50

        s0 = self._point_by_date(result, date(2026, 4, 30))
        self.assertEqual(s0.planned_completed_daily, 0)
        self.assertEqual(s0.planned_remaining, 150)
        self.assertIsNone(s0.actual_completed_daily)
        self.assertEqual(s0.actual_remaining, 150)

        s1 = self._point_by_date(result, date(2026, 5, 1))
        self.assertEqual(s1.planned_completed_daily, 30)    # 20 + 10
        self.assertEqual(s1.planned_remaining, 120)         # 150 - 30
        self.assertEqual(s1.actual_completed_daily, 15)     # 10 + 5
        self.assertEqual(s1.actual_remaining, 135)          # 150 - 15


    def test_plan_case_mismatch_uses_available_cases_including_na(self):
        self._make_plan(label="TEST001", total=100, daily_counts=[20] * 5)
        _insert_file_progress(self.db, 1001, "TEST001", available=110, executed=10)

        from app.models.progress import FileProgress
        from sqlalchemy import select

        file_progress = self.db.scalar(select(FileProgress).where(FileProgress.testing_id == 1001))
        file_progress.result_na = 10
        self.db.commit()

        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertEqual(result.available_cases, 110)
        self.assertEqual(result.actual_na_cases, 10)
        self.assertEqual(result.actual_plan_comparable_cases, 110)
        self.assertTrue(result.plan_case_mismatch)

        file_progress.result_na = 9
        self.db.commit()

        result = get_pb_chart(self.db, 1001, label="TEST001")
        self.assertEqual(result.actual_plan_comparable_cases, 110)
        self.assertTrue(result.plan_case_mismatch)

    def test_actual_remaining_uses_file_executed_total_when_daily_is_short(self):
        self._make_plan(label="TEST001", total=112, daily_counts=[28] * 4)
        _insert_file_progress(self.db, 1001, "TEST001", available=112, executed=78)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 30),
            ("TEST001", date(2026, 5, 2), 39),
        ])

        result = get_pb_chart(self.db, 1001, label=None)

        self.assertEqual(result.available_cases, 112)
        self.assertEqual(result.undated_result_cases, 9)
        self.assertEqual(self._point_by_date(result, date(2026, 4, 30)).actual_remaining, 112)
        self.assertEqual(self._point_by_date(result, date(2026, 5, 1)).actual_remaining, 73)
        self.assertEqual(self._point_by_date(result, date(2026, 5, 2)).actual_completed_daily, 39)
        self.assertEqual(self._point_by_date(result, date(2026, 5, 2)).actual_remaining, 34)

    def test_undated_result_cases_are_reported_without_daily_rows(self):
        self._make_plan(label="TEST001", total=100, daily_counts=[20] * 5)
        _insert_file_progress(self.db, 1001, "TEST001", available=100, executed=12)

        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertEqual(result.undated_result_cases, 12)
    def test_all_labels_counts_plan_only_label_as_actual_offset(self):
        self._make_plan(label="TEST001", total=100, daily_counts=[20] * 5)
        self._make_plan(label="TEST002", total=50, daily_counts=[10] * 5)
        _insert_file_progress(self.db, 1001, "TEST001", available=100, executed=10)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 10),
        ])

        result = get_pb_chart(self.db, 1001, label=None)

        self.assertEqual(result.planned_total_cases, 150)
        self.assertEqual(result.available_cases, 100)       # API metadata remains actual-file-only
        self.assertEqual(result.actual_total_cases, 150)
        self.assertIsNone(self._point_by_date(result, date(2026, 4, 30)).actual_completed_daily)
        self.assertEqual(self._point_by_date(result, date(2026, 4, 30)).actual_remaining, 150)
        self.assertEqual(self._point_by_date(result, date(2026, 5, 1)).actual_completed_daily, 10)
        self.assertEqual(self._point_by_date(result, date(2026, 5, 1)).actual_remaining, 140)
        self.assertFalse(result.plan_case_mismatch)


    def test_disabled_label_excluded_from_all_and_label_chart(self):
        self._make_plan(label="TEST001", total=100, daily_counts=[20] * 5)
        self._make_plan(label="TEST002", total=50, daily_counts=[10] * 5)
        create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST002", is_disabled=True))
        _insert_file_progress(self.db, 1001, "TEST001", available=100, executed=10)
        _insert_file_progress(self.db, 1001, "TEST002", available=50, executed=5)
        _insert_actuals(self.db, 1001, [
            ("TEST001", date(2026, 5, 1), 10),
            ("TEST002", date(2026, 5, 1), 5),
        ])

        result = get_pb_chart(self.db, 1001, label=None)

        self.assertEqual(result.planned_total_cases, 100)
        self.assertEqual(result.available_cases, 100)
        self.assertEqual(self._point_by_date(result, date(2026, 4, 30)).planned_completed_daily, 0)
        self.assertIsNone(self._point_by_date(result, date(2026, 4, 30)).actual_completed_daily)
        self.assertEqual(self._point_by_date(result, date(2026, 5, 1)).planned_completed_daily, 20)
        self.assertEqual(self._point_by_date(result, date(2026, 5, 1)).actual_completed_daily, 10)

        disabled_result = get_pb_chart(self.db, 1001, label="TEST002")
        self.assertIsNone(disabled_result.range)
        self.assertEqual(disabled_result.series, [])
        self.assertIsNone(disabled_result.planned_total_cases)
        self.assertEqual(disabled_result.available_cases, 0)

    # ---- 過去計画 ----

    def test_past_plans_returned(self):
        v1 = self._make_plan(total=80, daily_counts=[16] * 5, activate=True)
        v2 = self._make_plan(total=100, daily_counts=[20] * 5, activate=True)  # v1 が非有効に
        result = get_pb_chart(self.db, 1001, label="TEST001", include_past_plans=True)

        self.assertEqual(len(result.past_plans), 1)
        pp = result.past_plans[0]
        self.assertEqual(pp.version, 1)
        self.assertEqual(pp.planned_total_cases, 80)
        # 0日目: 80、1日目: 80 - 16 = 64
        self.assertEqual(pp.series[0].date, date(2026, 4, 30))
        self.assertEqual(pp.series[0].planned_remaining, 80)
        self.assertEqual(pp.series[0].planned_completed_daily, 0)
        self.assertEqual(pp.series[1].planned_remaining, 64)

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
        self.assertEqual(pp.series[0].planned_completed_daily, 0)
        self.assertEqual(pp.series[0].planned_remaining, 150)
        self.assertEqual(pp.series[1].planned_completed_daily, 30)  # 20 + 10
        self.assertEqual(pp.series[1].planned_remaining, 120)       # 150 - 30

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
        self.assertEqual(pp.series[0].planned_completed_daily, 0)
        self.assertEqual(pp.series[0].planned_remaining, 130)
        self.assertEqual(pp.series[1].planned_completed_daily, 26)  # 16 + 10
        self.assertEqual(pp.series[1].planned_remaining, 104)       # 130 - 26

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

    def test_bug_axis_max_uses_project_value_when_set(self):
        from app.crud.project import update_project
        from app.crud.setting import update_pb_chart_settings
        from app.schemas.project import ProjectUpdate
        from app.schemas.setting import PbChartSettings

        update_pb_chart_settings(self.db, PbChartSettings(bug_axis_max=60))
        update_project(self.db, 1001, ProjectUpdate(bug_axis_max=90))

        result = get_pb_chart(self.db, 1001)

        self.assertEqual(result.bug_axis_max, 90)

    def test_bug_axis_max_falls_back_to_global_setting(self):
        from app.crud.setting import update_pb_chart_settings
        from app.schemas.setting import PbChartSettings

        update_pb_chart_settings(self.db, PbChartSettings(bug_axis_max=60))

        result = get_pb_chart(self.db, 1001)

        self.assertEqual(result.bug_axis_max, 60)

    def test_test_result_bug_source_burndown(self):
        from app.crud.project import update_project
        from app.models.progress import TestResultBugSnapshot, Testing
        from app.schemas.project import ProjectUpdate
        from datetime import datetime
        from sqlalchemy import select

        update_project(self.db, 1001, ProjectUpdate(bug_count_source="test_result"))
        if not self.db.scalar(select(Testing).where(Testing.testing_id == 1001)):
            self.db.add(Testing(testing_id=1001, project_name="P1001", updated_at=datetime(2026, 5, 3, 12, 0)))
            self.db.flush()
        # detected = 検出増分, suspend/fixed = 現在値。
        self.db.add_all(
            [
                TestResultBugSnapshot(
                    testing_id=1001,
                    snapshot_date=date(2026, 5, 1),
                    detected_count=3,
                    suspend_count=1,
                    fixed_count=0,
                    sent_at=datetime(2026, 5, 1, 10, 0),
                ),
                TestResultBugSnapshot(
                    testing_id=1001,
                    snapshot_date=date(2026, 5, 3),
                    detected_count=1,
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
        # 未解消 = 検出累積 − 見送り累積 − 完了累積。
        # 5/1: 検出3 見送り1 完了0 → (open2, susp1, res0)
        # 5/2: 前日引き継ぎ → (2, 1, 0)
        # 5/3: 検出4 見送り2 完了2 → (open0, susp2, res2)
        self.assertEqual(
            [(item.bug_open, item.bug_suspended, item.bug_resolved) for item in result.series],
            [(2, 1, 0), (2, 1, 0), (0, 2, 2)],
        )

    def test_test_result_bug_source_per_label(self):
        """テスト結果ソースは label 別に不具合を取得でき、(全て)では合算される。"""
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
                # TEST001: 5/1 検出2 見送り0 完了0、5/3 検出1 完了1
                TestResultBugSnapshot(
                    testing_id=1001, label="TEST001", snapshot_date=date(2026, 5, 1),
                    detected_count=2, suspend_count=0, fixed_count=0, sent_at=datetime(2026, 5, 1, 10, 0),
                ),
                TestResultBugSnapshot(
                    testing_id=1001, label="TEST001", snapshot_date=date(2026, 5, 3),
                    detected_count=1, suspend_count=0, fixed_count=1, sent_at=datetime(2026, 5, 3, 10, 0),
                ),
                # TEST002: 5/2 検出3 見送り1
                TestResultBugSnapshot(
                    testing_id=1001, label="TEST002", snapshot_date=date(2026, 5, 2),
                    detected_count=3, suspend_count=1, fixed_count=0, sent_at=datetime(2026, 5, 2, 10, 0),
                ),
            ]
        )
        self.db.commit()

        # TEST001 のみ: 5/1 検出2 → open2、5/3 検出累積3・完了1 → open2 完了1
        result = get_pb_chart(self.db, 1001, label="TEST001")
        self.assertTrue(result.has_bugs)
        self.assertEqual(result.range, {"from": "2026-05-01", "to": "2026-05-03"})
        self.assertEqual(
            [(s.bug_open, s.bug_suspended, s.bug_resolved) for s in result.series],
            [(2, 0, 0), (2, 0, 0), (2, 0, 1)],
        )

        # (全て): TEST001 + TEST002 を日付ごとに合算
        # 5/1 検出2 → (2,0,0)
        # 5/2 検出累積5・見送り1 → open4 見送り1
        # 5/3 検出累積6・見送り1・完了1 → open4 見送り1 完了1
        result_all = get_pb_chart(self.db, 1001, label=None)
        self.assertEqual(
            [(s.bug_open, s.bug_suspended, s.bug_resolved) for s in result_all.series],
            [(2, 0, 0), (4, 1, 0), (4, 1, 1)],
        )

    def test_project_period_range_source_uses_project_planned_dates(self):
        from app.crud.project import update_project
        from app.schemas.project import ProjectUpdate

        self._make_plan(total=100, daily_counts=[20] * 5)
        update_project(
            self.db,
            1001,
            ProjectUpdate(
                planned_start_date=date(2026, 4, 30),
                planned_end_date=date(2026, 5, 10),
                pb_chart_range_source="project_period",
            ),
        )

        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertEqual(result.range, {"from": "2026-04-29", "to": "2026-05-10"})
        self.assertEqual(len(result.series), 12)
        self.assertIsNone(result.series[0].planned_remaining)
        self.assertEqual(result.series[1].planned_remaining, 100)
        self.assertEqual(result.series[2].planned_remaining, 80)
        self.assertEqual(result.series[6].planned_remaining, 0)
        self.assertIsNone(result.series[-1].planned_remaining)

    def test_project_period_range_source_falls_back_without_project_planned_dates(self):
        from app.crud.project import update_project
        from app.schemas.project import ProjectUpdate

        self._make_plan(total=100, daily_counts=[20] * 5)
        update_project(self.db, 1001, ProjectUpdate(pb_chart_range_source="project_period"))

        result = get_pb_chart(self.db, 1001, label="TEST001")

        self.assertEqual(result.range, {"from": "2026-04-30", "to": "2026-05-05"})
        self.assertEqual(len(result.series), 6)
    def test_azure_devops_bug_dates_do_not_expand_plan_actual_range(self):
        from app.models.bug import BugSnapshot
        from datetime import datetime

        self._make_plan(total=100, daily_counts=[20] * 5)
        self.db.add_all(
            [
                BugSnapshot(
                    testing_id=1001,
                    bug_work_item_id=9001,
                    title="before range",
                    state="Active",
                    created_date=date(2026, 4, 25),
                    finish_date=None,
                    fetched_at=datetime(2026, 5, 20, 12, 0),
                ),
                BugSnapshot(
                    testing_id=1001,
                    bug_work_item_id=9002,
                    title="after range",
                    state="Active",
                    created_date=date(2026, 5, 10),
                    finish_date=None,
                    fetched_at=datetime(2026, 5, 20, 12, 0),
                ),
            ]
        )
        self.db.commit()

        result = get_pb_chart(self.db, 1001, label=None)

        self.assertTrue(result.has_bugs)
        self.assertEqual(result.range, {"from": "2026-04-30", "to": "2026-05-05"})
        self.assertEqual(len(result.series), 6)
        self.assertEqual(
            [item.date for item in result.series],
            [date(2026, 4, 30), *[date(2026, 5, day) for day in range(1, 6)]],
        )
        self.assertEqual(
            [(item.bug_open, item.bug_suspended, item.bug_resolved) for item in result.series],
            [(1, 0, 0)] * 6,
        )

    def test_test_result_bug_dates_do_not_expand_plan_actual_range(self):
        from app.crud.project import update_project
        from app.models.progress import TestResultBugSnapshot, Testing
        from app.schemas.project import ProjectUpdate
        from datetime import datetime
        from sqlalchemy import select

        update_project(self.db, 1001, ProjectUpdate(bug_count_source="test_result"))
        self._make_plan(total=100, daily_counts=[20] * 5)
        if not self.db.scalar(select(Testing).where(Testing.testing_id == 1001)):
            self.db.add(Testing(
                testing_id=1001,
                project_name="P1001",
                updated_at=datetime(2026, 5, 3, 12, 0),
            ))
            self.db.flush()
        self.db.add_all(
            [
                TestResultBugSnapshot(
                    testing_id=1001,
                    snapshot_date=date(2026, 4, 30),
                    detected_count=2,
                    suspend_count=0,
                    fixed_count=0,
                    sent_at=datetime(2026, 4, 30, 10, 0),
                ),
                TestResultBugSnapshot(
                    testing_id=1001,
                    snapshot_date=date(2026, 5, 3),
                    detected_count=1,
                    suspend_count=0,
                    fixed_count=0,
                    sent_at=datetime(2026, 5, 3, 10, 0),
                ),
                TestResultBugSnapshot(
                    testing_id=1001,
                    snapshot_date=date(2026, 5, 10),
                    detected_count=5,
                    suspend_count=0,
                    fixed_count=0,
                    sent_at=datetime(2026, 5, 10, 10, 0),
                ),
            ]
        )
        self.db.commit()

        result = get_pb_chart(self.db, 1001, label=None)

        self.assertTrue(result.has_bugs)
        self.assertEqual(result.range, {"from": "2026-04-30", "to": "2026-05-05"})
        self.assertEqual(len(result.series), 6)
        self.assertEqual(
            [(item.bug_open, item.bug_suspended, item.bug_resolved) for item in result.series],
            [(2, 0, 0), (2, 0, 0), (2, 0, 0), (3, 0, 0), (3, 0, 0), (3, 0, 0)],
        )

    # ---- 存在しないプロジェクト ----

    def test_unknown_project_raises(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            get_pb_chart(self.db, 9999)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
