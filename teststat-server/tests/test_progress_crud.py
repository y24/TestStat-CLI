import os
import sys
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.crud.progress import get_daily_progress, get_file_progress, get_progress_summary, replace_progress  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.progress import DailyPersonProgress, DailyProgress, FileProgress  # noqa: E402
from app.schemas.progress import ProgressRequest  # noqa: E402


def make_payload(testing_id=1001, file_name="sample1.xlsx", pass_count=4, available_cases=8):
    return ProgressRequest.model_validate(
        {
            "testing_id": testing_id,
            "project_name": f"Project {testing_id}",
            "sender": "sender-a",
            "sent_at": "2026-05-31T10:00:00",
            "files": [
                {
                    "file_name": file_name,
                    "label": "TEST001",
                    "environment": "env-a",
                    "total_cases": 10,
                    "available_cases": available_cases,
                    "excluded_cases": 2,
                    "completed": 5,
                    "executed": 6,
                    "not_run": 2,
                    "completed_rate": 62.5,
                    "executed_rate": 75.0,
                    "start_date": "2026-05-01",
                    "latest_update": "2026-05-02",
                    "results": {
                        "Pass": pass_count,
                        "Fixed": 1,
                        "Fail": 1,
                        "Blocked": 0,
                        "Suspend": 0,
                        "N/A": 0,
                    },
                    "daily": [
                        {
                            "date": "2026-05-01",
                            "Pass": pass_count,
                            "Fixed": 1,
                            "Fail": 1,
                            "Blocked": 0,
                            "Suspend": 0,
                            "N/A": 0,
                            "completed": 5,
                            "executed": 6,
                            "planned": None,
                        }
                    ],
                    "by_person": [
                        {"date": "2026-05-01", "person": "Alice", "count": 3},
                        {"date": "2026-05-01", "person": "Bob", "count": 3},
                    ],
                }
            ],
        }
    )


class ProgressCrudTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_replace_progress_inserts_and_summarizes_rows(self):
        response = replace_progress(self.db, make_payload())

        self.assertEqual(response.inserted_files, 1)
        self.assertEqual(response.inserted_daily_rows, 1)
        self.assertEqual(response.inserted_person_rows, 2)

        summary = get_progress_summary(self.db, 1001)
        self.assertIsNotNone(summary)
        self.assertEqual(summary.summary.available_cases, 8)
        self.assertEqual(summary.results.pass_count, 4)

        files = get_file_progress(self.db, 1001)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].sender, "sender-a")

        daily = get_daily_progress(self.db, 1001)
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0].pass_count, 4)

    def test_replace_progress_refreshes_only_matching_testing_id(self):
        replace_progress(self.db, make_payload(testing_id=1001, file_name="old.xlsx", pass_count=4))
        replace_progress(self.db, make_payload(testing_id=2002, file_name="other.xlsx", pass_count=8))
        replace_progress(self.db, make_payload(testing_id=1001, file_name="new.xlsx", pass_count=2))

        testing_1001_files = get_file_progress(self.db, 1001)
        testing_2002_files = get_file_progress(self.db, 2002)

        self.assertEqual([row.file_name for row in testing_1001_files], ["new.xlsx"])
        self.assertEqual([row.file_name for row in testing_2002_files], ["other.xlsx"])
        self.assertEqual(get_progress_summary(self.db, 1001).results.pass_count, 2)
        self.assertEqual(get_progress_summary(self.db, 2002).results.pass_count, 8)

    def test_validation_failure_does_not_delete_existing_rows(self):
        replace_progress(self.db, make_payload())

        invalid_payload = ProgressRequest.model_validate(
            {
                "testing_id": 1001,
                "project_name": "Project 1001",
                "files": [],
            }
        )

        with self.assertRaises(Exception):
            replace_progress(self.db, invalid_payload)

        self.assertEqual(len(get_file_progress(self.db, 1001)), 1)
        self.assertEqual(len(self.db.scalars(select(DailyProgress).where(DailyProgress.testing_id == 1001)).all()), 1)
        self.assertEqual(len(self.db.scalars(select(DailyPersonProgress).where(DailyPersonProgress.testing_id == 1001)).all()), 2)

    def test_archived_project_rejects_replace_without_deleting_existing_rows(self):
        replace_progress(self.db, make_payload(testing_id=3003, file_name="old.xlsx", pass_count=4))
        self.db.add(Project(testing_id=3003, name="Archived Project", archived=True))
        self.db.commit()

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            replace_progress(self.db, make_payload(testing_id=3003, file_name="new.xlsx", pass_count=9))

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual([row.file_name for row in get_file_progress(self.db, 3003)], ["old.xlsx"])
        self.assertEqual(get_progress_summary(self.db, 3003).results.pass_count, 4)


if __name__ == "__main__":
    unittest.main()
