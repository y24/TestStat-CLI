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


if __name__ == "__main__":
    unittest.main()
