import os
import sys
import unittest

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: F401,E402
from app.crud.plan import create_plan_label  # noqa: E402
from app.crud.project import create_project, update_project  # noqa: E402
from app.database import Base  # noqa: E402
from app.schemas.plan import PlanLabelCreate  # noqa: E402
from app.schemas.project import ProjectCreate, ProjectUpdate  # noqa: E402
from app.services.collector import CollectFile, CollectTarget, build_list_yaml, count_collect_targets, _load_targets  # noqa: E402


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return Session()


class TestCollector(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        create_project(self.db, ProjectCreate(testing_id=3001, name="Project A"))
        create_project(self.db, ProjectCreate(testing_id=3002, name="Project B"))

    def tearDown(self):
        self.db.close()

    def test_build_list_yaml(self):
        yaml_text = build_list_yaml(
            CollectTarget(
                testing_id=3001,
                project_name="Project A",
                files=(
                    CollectFile(
                        label="LABEL1",
                        source_url="https://contoso.sharepoint.com/:x:/s/a?x=1",
                        target_sheets=("テスト項目",),
                        ignore_sheets=("Sheet1",),
                        include_hidden_sheets=False,
                        target_environments=("環境a",),
                    ),
                ),
            )
        )
        self.assertNotIn('project:', yaml_text)
        self.assertIn('project_name: "Project A"', yaml_text)
        self.assertIn("testing_id: 3001", yaml_text)
        self.assertIn('label: "LABEL1"', yaml_text)
        self.assertIn('path: "https://contoso.sharepoint.com/:x:/s/a?x=1"', yaml_text)
        self.assertIn('target_sheets:', yaml_text)
        self.assertIn('    - "テスト項目"', yaml_text)
        self.assertIn('ignore_sheets:', yaml_text)
        self.assertIn('    - "Sheet1"', yaml_text)
        self.assertIn('include_hidden_sheets: false', yaml_text)
        self.assertIn('target_environments:', yaml_text)
        self.assertIn('    - "環境a"', yaml_text)

    def test_load_targets_excludes_empty_and_archived(self):
        create_plan_label(self.db, 3001, PlanLabelCreate(label="A", source_url="https://example.com/a.xlsx"))
        create_plan_label(self.db, 3001, PlanLabelCreate(label="B", source_url=""))
        create_plan_label(self.db, 3002, PlanLabelCreate(label="C", source_url="https://example.com/c.xlsx"))
        update_project(self.db, 3002, ProjectUpdate(archived=True))

        self.assertEqual(count_collect_targets(self.db), 1)
        targets = _load_targets(self.db)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].testing_id, 3001)
        self.assertEqual(targets[0].files, (CollectFile(label="A", source_url="https://example.com/a.xlsx"),))

    def test_load_targets_filters_by_label(self):
        create_plan_label(self.db, 3001, PlanLabelCreate(label="A", source_url="https://example.com/a.xlsx"))
        create_plan_label(self.db, 3001, PlanLabelCreate(label="B", source_url="https://example.com/b.xlsx"))

        targets = _load_targets(self.db, testing_id=3001, label="B")
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].files, (CollectFile(label="B", source_url="https://example.com/b.xlsx"),))

        # URL 未登録の識別子は対象外（情報更新ボタンが押せないケース）
        create_plan_label(self.db, 3001, PlanLabelCreate(label="C", source_url=""))
        self.assertEqual(_load_targets(self.db, testing_id=3001, label="C"), [])

    def test_load_targets_includes_cli_options(self):
        create_plan_label(
            self.db,
            3001,
            PlanLabelCreate(
                label="A",
                source_url="https://example.com/a.xlsx",
                target_sheets=[" テスト項目 "],
                ignore_sheets=["Sheet1"],
                include_hidden_sheets=True,
                target_environments=["環境a"],
                ignore_environments=["環境b"],
            ),
        )

        targets = _load_targets(self.db, testing_id=3001, label="A")
        self.assertEqual(
            targets[0].files,
            (
                CollectFile(
                    label="A",
                    source_url="https://example.com/a.xlsx",
                    target_sheets=("テスト項目",),
                    ignore_sheets=("Sheet1",),
                    include_hidden_sheets=True,
                    target_environments=("環境a",),
                    ignore_environments=("環境b",),
                ),
            ),
        )


if __name__ == "__main__":
    unittest.main()
