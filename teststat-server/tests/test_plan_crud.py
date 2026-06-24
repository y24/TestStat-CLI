import os
import sys
import unittest
from datetime import date, datetime

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine, event, select, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: F401  — 全モデルを Base.metadata に登録
from app.crud.plan import (  # noqa: E402
    activate_plan,
    create_plan,
    create_plan_label,
    delete_plan,
    delete_plan_label,
    delete_project_label,
    get_plan_detail,
    list_plan_labels,
    list_plans,
    update_plan_label,
    update_plan_label_order,
    update_project_label,
)
from app.crud.project import create_project, update_project  # noqa: E402
from app.models.progress import (  # noqa: E402
    DailyPersonProgress,
    DailyProgress,
    FileProgress,
    TestResultBugSnapshot as BugSnapshotModel,
    Testing as TestingModel,
)
from app.database import Base  # noqa: E402
from app.schemas.plan import PlanCreate, PlanDailyIn, PlanLabelCreate, PlanLabelOrderUpdate, PlanLabelUpdate, ProjectLabelUpdate  # noqa: E402
from app.schemas.project import ProjectCreate, ProjectUpdate  # noqa: E402


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

    def test_create_and_list_plan_labels(self):
        created = create_plan_label(self.db, 1001, PlanLabelCreate(label="  TEST001  "))
        self.assertEqual(created.label, "TEST001")
        self.assertFalse(created.is_disabled)
        self.assertEqual(created.display_order, 0)

        labels = list_plan_labels(self.db, 1001)
        self.assertEqual([label.label for label in labels], ["TEST001"])
        self.assertFalse(labels[0].is_disabled)

    def test_update_plan_label_order(self):
        first = create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST001"))
        second = create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST002"))
        third = create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST003"))

        ordered = update_plan_label_order(
            self.db,
            1001,
            PlanLabelOrderUpdate(label_ids=[third.id, first.id, second.id]),
        )

        self.assertEqual([label.label for label in ordered], ["TEST003", "TEST001", "TEST002"])
        self.assertEqual([label.display_order for label in ordered], [0, 1, 2])

    def test_update_plan_label_order_materializes_actual_only_label(self):
        self._insert_actual_label("CLI_LABEL")
        existing = create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST001"))

        ordered = update_plan_label_order(
            self.db,
            1001,
            PlanLabelOrderUpdate(labels=["CLI_LABEL", existing.label]),
        )

        self.assertEqual([label.label for label in ordered], ["CLI_LABEL", "TEST001"])
        self.assertEqual([label.display_order for label in ordered], [0, 1])



    def _insert_actual_label(self, label="CLI_LABEL"):
        if self.db.scalar(select(TestingModel).where(TestingModel.testing_id == 1001)) is None:
            self.db.add(TestingModel(testing_id=1001, project_name="テストP"))
            self.db.commit()
        self.db.add_all([
            FileProgress(
                testing_id=1001, file_name="cli.xlsx", label=label, environment=None,
                total_cases=10, available_cases=10, excluded_cases=0, completed=1, executed=1,
                not_run=9, completed_rate=10, executed_rate=10, result_pass=1, result_fixed=0,
                result_fail=0, result_blocked=0, result_suspend=0, result_na=0,
                start_date=START, latest_update=START, sent_at=datetime(2026, 5, 1),
            ),
            DailyProgress(
                testing_id=1001, file_name="cli.xlsx", label=label, environment=None, date=START,
                result_pass=1, result_fixed=0, result_fail=0, result_blocked=0, result_suspend=0,
                result_na=0, completed=1, executed=1, planned=None,
            ),
            DailyPersonProgress(
                testing_id=1001, file_name="cli.xlsx", label=label, environment=None, date=START,
                person="tester", count=1,
            ),
            BugSnapshotModel(
                testing_id=1001, label=label, snapshot_date=START, detected_count=1,
                suspend_count=0, fixed_count=0, sent_at=datetime(2026, 5, 1),
            ),
        ])
        self.db.commit()

    def test_update_project_label_renames_cli_actuals_and_plans(self):
        self._insert_actual_label("CLI_LABEL")
        create_plan(self.db, 1001, self._make_plan("CLI_LABEL"))

        updated = update_project_label(
            self.db,
            1001,
            ProjectLabelUpdate(old_label="CLI_LABEL", label="RENAMED_LABEL"),
        )

        self.assertEqual(updated.label, "RENAMED_LABEL")
        self.assertEqual(self.db.scalar(select(FileProgress.label)), "RENAMED_LABEL")
        self.assertEqual(self.db.scalar(select(DailyProgress.label)), "RENAMED_LABEL")
        self.assertEqual(self.db.scalar(select(DailyPersonProgress.label)), "RENAMED_LABEL")
        self.assertEqual(self.db.scalar(select(BugSnapshotModel.label)), "RENAMED_LABEL")
        self.assertEqual([plan.label for plan in list_plans(self.db, 1001)], ["RENAMED_LABEL"])


    def test_update_project_label_with_empty_old_label_creates_plan_label_metadata(self):
        updated = update_project_label(
            self.db,
            1001,
            ProjectLabelUpdate(
                old_label="",
                label="123556",
                source_url="http://saitheaihgioagagdabha",
                target_sheets=["ああああ"],
                ignore_sheets=["いいい", "っっっy"],
                include_hidden_sheets=None,
                target_environments=["あああああああ"],
                ignore_environments=["111111"],
            ),
        )

        self.assertEqual(updated.label, "123556")
        self.assertEqual(updated.source_url, "http://saitheaihgioagagdabha")
        self.assertEqual(updated.target_sheets, ["ああああ"])
        self.assertEqual(updated.ignore_sheets, ["いいい", "っっっy"])
        self.assertIsNone(updated.include_hidden_sheets)
        self.assertEqual(updated.target_environments, ["あああああああ"])
        self.assertEqual(updated.ignore_environments, ["111111"])

    def test_update_project_label_with_empty_old_label_updates_existing_metadata(self):
        create_plan_label(self.db, 1001, PlanLabelCreate(label="123556", source_url="http://old.example"))

        updated = update_project_label(
            self.db,
            1001,
            ProjectLabelUpdate(old_label="", label="123556", source_url="http://new.example", target_sheets=["更新後"]),
        )

        self.assertEqual(updated.label, "123556")
        self.assertEqual(updated.source_url, "http://new.example")
        self.assertEqual(updated.target_sheets, ["更新後"])

    def test_delete_project_label_deletes_cli_actuals_and_plans(self):
        self._insert_actual_label("CLI_LABEL")
        create_plan(self.db, 1001, self._make_plan("CLI_LABEL"))

        delete_project_label(self.db, 1001, "CLI_LABEL")

        self.assertIsNone(self.db.scalar(select(FileProgress)))
        self.assertIsNone(self.db.scalar(select(DailyProgress)))
        self.assertIsNone(self.db.scalar(select(DailyPersonProgress)))
        self.assertIsNone(self.db.scalar(select(BugSnapshotModel)))
        self.assertEqual(list_plans(self.db, 1001), [])


    def test_update_plan_label_disabled_flag(self):
        label = create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST001"))

        updated = update_plan_label(self.db, label.id, PlanLabelUpdate(label="TEST001", is_disabled=True))

        self.assertTrue(updated.is_disabled)
        self.assertTrue(list_plan_labels(self.db, 1001)[0].is_disabled)

    def test_update_plan_label_renames_related_plans(self):
        label = create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST001"))
        create_plan(self.db, 1001, self._make_plan("TEST001"))

        updated = update_plan_label(self.db, label.id, PlanLabelUpdate(label="TEST-RENAMED"))

        self.assertEqual(updated.label, "TEST-RENAMED")
        labels = [item.label for item in list_plan_labels(self.db, 1001)]
        self.assertEqual(labels, ["TEST-RENAMED"])
        plans = list_plans(self.db, 1001)
        self.assertEqual([plan.label for plan in plans], ["TEST-RENAMED"])

    def test_update_plan_label_duplicate_raises(self):
        from fastapi import HTTPException

        first = create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST001"))
        create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST002"))
        with self.assertRaises(HTTPException) as ctx:
            update_plan_label(self.db, first.id, PlanLabelUpdate(label="TEST002"))
        self.assertEqual(ctx.exception.status_code, 409)

    def test_delete_plan_label_deletes_related_plans(self):
        label = create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST001"))
        create_plan(self.db, 1001, self._make_plan("TEST001"))

        delete_plan_label(self.db, label.id)

        self.assertEqual(list_plan_labels(self.db, 1001), [])
        self.assertEqual(list_plans(self.db, 1001), [])

    def test_duplicate_plan_label_raises(self):
        from fastapi import HTTPException

        create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST001"))
        with self.assertRaises(HTTPException) as ctx:
            create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST001"))
        self.assertEqual(ctx.exception.status_code, 409)

    def test_archived_project_rejects_plan_label_mutations(self):
        from fastapi import HTTPException

        label = create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST001"))
        update_project(self.db, 1001, ProjectUpdate(archived=True))

        operations = [
            lambda: create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST002")),
            lambda: update_project_label(self.db, 1001, ProjectLabelUpdate(old_label="TEST001", label="RENAMED")),
            lambda: update_plan_label(self.db, label.id, PlanLabelUpdate(label="TEST001", is_disabled=True)),
            lambda: update_plan_label_order(self.db, 1001, PlanLabelOrderUpdate(label_ids=[label.id])),
            lambda: delete_project_label(self.db, 1001, "TEST001"),
        ]

        for operation in operations:
            with self.assertRaises(HTTPException) as ctx:
                operation()
            self.assertEqual(ctx.exception.status_code, 409)

    def test_archived_project_rejects_plan_mutations(self):
        from fastapi import HTTPException

        first = create_plan(self.db, 1001, self._make_plan(activate=True))
        second = create_plan(self.db, 1001, self._make_plan(activate=False))
        update_project(self.db, 1001, ProjectUpdate(archived=True))

        operations = [
            lambda: create_plan(self.db, 1001, self._make_plan("TEST002")),
            lambda: activate_plan(self.db, second.id),
            lambda: delete_plan(self.db, first.id),
        ]

        for operation in operations:
            with self.assertRaises(HTTPException) as ctx:
                operation()
            self.assertEqual(ctx.exception.status_code, 409)


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


    def test_project_summary_excludes_disabled_label(self):
        from app.crud.project import get_project

        create_plan(self.db, 1001, self._make_plan("TEST001", total=100, activate=True))
        create_plan(self.db, 1001, self._make_plan("TEST002", total=50, activate=True))
        create_plan_label(self.db, 1001, PlanLabelCreate(label="TEST002", is_disabled=True))
        self._insert_actual_label("TEST001")
        self._insert_actual_label("TEST002")

        project = get_project(self.db, 1001)

        self.assertEqual(project.active_plan_count, 1)
        self.assertEqual(project.actual_available_cases, 10)

    def test_project_active_plan_count(self):
        from app.crud.project import get_project
        create_plan(self.db, 1001, self._make_plan("TEST001", activate=True))
        create_plan(self.db, 1001, self._make_plan("TEST002", activate=True))
        p = get_project(self.db, 1001)
        self.assertEqual(p.active_plan_count, 2)


if __name__ == "__main__":
    unittest.main()

class TestPlanLabelSourceUrl(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        create_project(self.db, ProjectCreate(testing_id=2001, name="URL Test"))

    def tearDown(self):
        self.db.close()

    def test_create_update_and_clear_source_url(self):
        created = create_plan_label(
            self.db,
            2001,
            PlanLabelCreate(label="URL_LABEL", source_url="  https://contoso.sharepoint.com/:x:/s/a  "),
        )
        self.assertEqual(created.source_url, "https://contoso.sharepoint.com/:x:/s/a")

        updated = update_plan_label(
            self.db,
            created.id,
            PlanLabelUpdate(label="URL_LABEL", source_url="https://contoso.sharepoint.com/:x:/s/b"),
        )
        self.assertEqual(updated.label, "URL_LABEL")
        self.assertEqual(updated.source_url, "https://contoso.sharepoint.com/:x:/s/b")

        cleared = update_project_label(
            self.db,
            2001,
            ProjectLabelUpdate(old_label="URL_LABEL", label="URL_RENAMED", source_url=""),
        )
        self.assertEqual(cleared.label, "URL_RENAMED")
        self.assertIsNone(cleared.source_url)

    def test_invalid_source_url_validation(self):
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            PlanLabelCreate(label="URL_LABEL", source_url="ftp://example.com/file.xlsx")

if __name__ == "__main__":
    unittest.main()
