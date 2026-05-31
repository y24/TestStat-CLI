import os
import sys
import unittest

from sqlalchemy import create_engine

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.crud.project import create_project, delete_project, get_project, list_projects, update_project  # noqa: E402
from app.database import Base  # noqa: E402
from app.models import Project  # noqa: E402
from app.schemas.project import ProjectCreate, ProjectUpdate  # noqa: E402


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    # 全モデルを import して Base.metadata に登録させる
    import app.models  # noqa: F401
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return Session()


class TestProjectCRUD(unittest.TestCase):
    def setUp(self):
        self.db = make_session()

    def tearDown(self):
        self.db.close()

    def test_create_and_list(self):
        create_project(self.db, ProjectCreate(testing_id=1001, name="プロジェクトA"))
        create_project(self.db, ProjectCreate(testing_id=1002, name="プロジェクトB", ticket_ref="TICKET-2"))
        result = list_projects(self.db)
        self.assertEqual(len(result), 2)
        ids = {r.testing_id for r in result}
        self.assertIn(1001, ids)
        self.assertIn(1002, ids)

    def test_create_duplicate_raises(self):
        create_project(self.db, ProjectCreate(testing_id=1001, name="A"))
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            create_project(self.db, ProjectCreate(testing_id=1001, name="B"))
        self.assertEqual(ctx.exception.status_code, 409)

    def test_get_project(self):
        create_project(self.db, ProjectCreate(testing_id=2001, name="取得テスト"))
        p = get_project(self.db, 2001)
        self.assertEqual(p.name, "取得テスト")
        self.assertFalse(p.has_actuals)
        self.assertIsNone(p.actuals_updated_at)
        self.assertEqual(p.active_plan_count, 0)

    def test_get_not_found_raises(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            get_project(self.db, 9999)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_update_name(self):
        create_project(self.db, ProjectCreate(testing_id=3001, name="旧名称"))
        updated = update_project(self.db, 3001, ProjectUpdate(name="新名称"))
        self.assertEqual(updated.name, "新名称")

    def test_update_archived(self):
        create_project(self.db, ProjectCreate(testing_id=3002, name="アーカイブ対象"))
        updated = update_project(self.db, 3002, ProjectUpdate(archived=True))
        self.assertTrue(updated.archived)

    def test_delete(self):
        create_project(self.db, ProjectCreate(testing_id=4001, name="削除対象"))
        delete_project(self.db, 4001)
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            get_project(self.db, 4001)

    def test_delete_archived_project_raises(self):
        create_project(self.db, ProjectCreate(testing_id=4002, name="削除不可対象"))
        update_project(self.db, 4002, ProjectUpdate(archived=True))

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            delete_project(self.db, 4002)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertTrue(get_project(self.db, 4002).archived)

    def test_has_actuals_when_testing_exists(self):
        from app.models.progress import Testing
        from datetime import datetime
        # testings に直接レコードを挿入して実績アリの状態を作る
        t = Testing(testing_id=5001, project_name="CLI Project", updated_at=datetime(2026, 5, 20, 18, 0))
        self.db.add(t)
        self.db.commit()
        create_project(self.db, ProjectCreate(testing_id=5001, name="実績ありP"))
        p = get_project(self.db, 5001)
        self.assertTrue(p.has_actuals)
        self.assertIsNotNone(p.actuals_updated_at)

    def test_actual_summary_when_file_progress_exists(self):
        from app.models.progress import FileProgress, Testing
        from datetime import datetime

        t = Testing(testing_id=5002, project_name="CLI Project", updated_at=datetime(2026, 5, 20, 18, 0))
        self.db.add(t)
        self.db.add_all(
            [
                FileProgress(
                    testing_id=5002,
                    file_name="a.xlsx",
                    total_cases=10,
                    available_cases=10,
                    completed=10,
                    executed=10,
                    completed_rate=100,
                    sent_at=datetime(2026, 5, 20, 18, 0),
                ),
                FileProgress(
                    testing_id=5002,
                    file_name="b.xlsx",
                    total_cases=5,
                    available_cases=5,
                    completed=3,
                    executed=4,
                    completed_rate=60,
                    sent_at=datetime(2026, 5, 20, 18, 0),
                ),
            ]
        )
        self.db.commit()
        create_project(self.db, ProjectCreate(testing_id=5002, name="集計ありP"))

        p = get_project(self.db, 5002)

        self.assertEqual(p.actual_available_cases, 15)
        self.assertEqual(p.actual_completed, 13)
        self.assertEqual(p.actual_completed_rate, 86.67)
        self.assertFalse(p.actual_all_completed)

    def test_actual_all_completed_when_every_file_is_100_percent(self):
        from app.models.progress import FileProgress, Testing
        from datetime import datetime

        t = Testing(testing_id=5003, project_name="CLI Project", updated_at=datetime(2026, 5, 20, 18, 0))
        self.db.add(t)
        self.db.add_all(
            [
                FileProgress(
                    testing_id=5003,
                    file_name="a.xlsx",
                    total_cases=10,
                    available_cases=10,
                    completed=10,
                    executed=10,
                    completed_rate=100,
                    sent_at=datetime(2026, 5, 20, 18, 0),
                ),
                FileProgress(
                    testing_id=5003,
                    file_name="b.xlsx",
                    total_cases=5,
                    available_cases=5,
                    completed=5,
                    executed=5,
                    completed_rate=100,
                    sent_at=datetime(2026, 5, 20, 18, 0),
                ),
            ]
        )
        self.db.commit()
        create_project(self.db, ProjectCreate(testing_id=5003, name="完了P"))

        p = get_project(self.db, 5003)

        self.assertEqual(p.actual_completed_rate, 100)
        self.assertTrue(p.actual_all_completed)

    def test_actual_vs_plan_rate_uses_plan_until_latest_actual_date(self):
        from app.models.plan import Plan, PlanDaily
        from app.models.progress import DailyProgress, FileProgress, Testing
        from datetime import date, datetime

        self.db.add(Testing(testing_id=5004, project_name="CLI Project", updated_at=datetime(2026, 5, 31, 4, 42)))
        self.db.add(
            FileProgress(
                testing_id=5004,
                file_name="a.xlsx",
                total_cases=20,
                available_cases=20,
                completed=8,
                executed=10,
                completed_rate=40,
                sent_at=datetime(2026, 5, 31, 4, 42),
            )
        )
        self.db.commit()
        create_project(self.db, ProjectCreate(testing_id=5004, name="対計画率P"))

        plan = Plan(
            testing_id=5004,
            label=None,
            version=1,
            is_active=True,
            planned_total_cases=20,
            start_date=date(2026, 5, 30),
            end_date=date(2026, 6, 2),
        )
        self.db.add(plan)
        self.db.flush()
        self.db.add_all(
            [
                PlanDaily(plan_id=plan.id, date=date(2026, 5, 30), planned_count=4),
                PlanDaily(plan_id=plan.id, date=date(2026, 5, 31), planned_count=6),
                PlanDaily(plan_id=plan.id, date=date(2026, 6, 1), planned_count=5),
            ]
        )
        self.db.add_all(
            [
                DailyProgress(
                    testing_id=5004,
                    file_name="a.xlsx",
                    date=date(2026, 5, 30),
                    completed=4,
                    executed=4,
                ),
                DailyProgress(
                    testing_id=5004,
                    file_name="a.xlsx",
                    date=date(2026, 5, 31),
                    completed=4,
                    executed=6,
                ),
            ]
        )
        self.db.commit()

        p = get_project(self.db, 5004)

        self.assertEqual(p.actual_completed_rate, 40)
        self.assertEqual(p.actual_vs_plan_rate, 100)


if __name__ == "__main__":
    unittest.main()
