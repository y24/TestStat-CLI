import os
import sys
import unittest
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.crud.progress import get_daily_progress, get_file_progress, get_progress_summary, replace_progress  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.plan import PlanLabel  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.progress import DailyPersonProgress, DailyProgress, FileProgress, TestResultBugSnapshot  # noqa: E402
from app.schemas.progress import ProgressRequest  # noqa: E402


def make_payload(
    testing_id=1001,
    file_name="sample1.xlsx",
    pass_count=4,
    available_cases=8,
    daily_date="2026-05-01",
    extra_daily=None,
    source_url=None,
    cli_options=None,
):
    daily_rows = [
        {
            "date": daily_date,
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
    ]
    daily_rows.extend(extra_daily or [])
    file_payload = {
        "file_name": file_name,
        "label": "TEST001",
        "source_url": source_url,
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
        "daily": daily_rows,
        "by_person": [
            {"date": daily_date, "person": "Alice", "count": 3},
            {"date": daily_date, "person": "Bob", "count": 3},
        ],
    }
    if cli_options:
        file_payload.update(cli_options)
    return ProgressRequest.model_validate(
        {
            "testing_id": testing_id,
            "project_name": f"Project {testing_id}",
            "sent_at": "2026-05-31T10:00:00",
            "files": [file_payload],
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

        daily = get_daily_progress(self.db, 1001)
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0].pass_count, 4)

    def test_replace_progress_saves_source_url_as_plan_label(self):
        replace_progress(
            self.db,
            make_payload(source_url="https://contoso.sharepoint.com/:x:/s/site/Eabc"),
        )

        label = self.db.scalar(select(PlanLabel).where(PlanLabel.testing_id == 1001, PlanLabel.label == "TEST001"))

        self.assertIsNotNone(label)
        self.assertEqual(label.source_url, "https://contoso.sharepoint.com/:x:/s/site/Eabc")

    def test_replace_progress_updates_existing_plan_label_source_url(self):
        self.db.add(PlanLabel(testing_id=1001, label="TEST001", source_url=None))
        self.db.commit()

        replace_progress(
            self.db,
            make_payload(source_url="https://contoso.sharepoint.com/:x:/s/site/Eupdated"),
        )

        label = self.db.scalar(select(PlanLabel).where(PlanLabel.testing_id == 1001, PlanLabel.label == "TEST001"))
        self.assertEqual(label.source_url, "https://contoso.sharepoint.com/:x:/s/site/Eupdated")


    def test_replace_progress_saves_cli_options_as_plan_label(self):
        replace_progress(
            self.db,
            make_payload(
                source_url="https://contoso.sharepoint.com/:x:/s/site/Eabc",
                cli_options={
                    "target_sheets": [" テスト項目 "],
                    "ignore_sheets": ["Sheet1"],
                    "include_hidden_sheets": False,
                    "target_environments": ["環境a"],
                    "ignore_environments": ["環境b"],
                },
            ),
        )

        label = self.db.scalar(select(PlanLabel).where(PlanLabel.testing_id == 1001, PlanLabel.label == "TEST001"))

        self.assertIsNotNone(label)
        self.assertEqual(label.source_url, "https://contoso.sharepoint.com/:x:/s/site/Eabc")
        self.assertEqual(label.target_sheets, ["テスト項目"])
        self.assertEqual(label.ignore_sheets, ["Sheet1"])
        self.assertIs(label.include_hidden_sheets, False)
        self.assertEqual(label.target_environments, ["環境a"])
        self.assertEqual(label.ignore_environments, ["環境b"])

    def test_replace_progress_preserves_plan_label_options_when_payload_omits_them(self):
        self.db.add(
            PlanLabel(
                testing_id=1001,
                label="TEST001",
                source_url="https://contoso.sharepoint.com/:x:/s/site/Eold",
                target_sheets=["テスト項目"],
                ignore_sheets=["Sheet1"],
                include_hidden_sheets=True,
                target_environments=["環境a"],
                ignore_environments=["環境b"],
            )
        )
        self.db.commit()

        replace_progress(self.db, make_payload(source_url="https://contoso.sharepoint.com/:x:/s/site/Eupdated"))

        label = self.db.scalar(select(PlanLabel).where(PlanLabel.testing_id == 1001, PlanLabel.label == "TEST001"))
        self.assertEqual(label.source_url, "https://contoso.sharepoint.com/:x:/s/site/Eupdated")
        self.assertEqual(label.target_sheets, ["テスト項目"])
        self.assertEqual(label.ignore_sheets, ["Sheet1"])
        self.assertIs(label.include_hidden_sheets, True)
        self.assertEqual(label.target_environments, ["環境a"])
        self.assertEqual(label.ignore_environments, ["環境b"])

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

    def test_replace_progress_stores_detected_and_current_states_by_date(self):
        # 単一取込。detected = その日の検出数(Fail+Suspend+Fixed)、suspend/fixed は現在値。
        payload = make_payload(
            testing_id=1001,
            pass_count=4,
            extra_daily=[
                {
                    "date": "2026-05-02",
                    "Pass": 3,
                    "Fixed": 2,
                    "Fail": 0,
                    "Blocked": 0,
                    "Suspend": 1,
                    "N/A": 0,
                    "completed": 6,
                    "executed": 6,
                    "planned": None,
                }
            ],
        )
        replace_progress(self.db, payload.model_copy(update={"sent_at": datetime(2026, 6, 1, 10, 0)}))

        rows = self.db.scalars(
            select(TestResultBugSnapshot)
            .where(TestResultBugSnapshot.testing_id == 1001)
            .order_by(TestResultBugSnapshot.snapshot_date)
        ).all()

        self.assertEqual([row.snapshot_date.isoformat() for row in rows], ["2026-05-01", "2026-05-02"])
        # 05-01: 検出=Fail1+Fixed1=2, 見送り0, 完了1 / 05-02: 検出=Suspend1+Fixed2=3, 見送り1, 完了2
        self.assertEqual(
            [(row.detected_count, row.suspend_count, row.fixed_count) for row in rows],
            [(2, 0, 1), (3, 1, 2)],
        )

    def test_replace_progress_keeps_detection_history_when_result_date_moves(self):
        # 1回目: 2026-05-01 に Fail1/Fixed1（検出2件）。
        replace_progress(self.db, make_payload(testing_id=1001, pass_count=4))
        # 2回目: 結果が変わり日付も移動し、2026-05-02 のみが入る（2026-05-01 はファイルから消える）。
        replacement = make_payload(testing_id=1001, pass_count=2, daily_date="2026-05-02")
        replacement.files[0].daily[0].fail = 0
        replacement.files[0].daily[0].fixed = 2
        replace_progress(self.db, replacement)

        rows = self.db.scalars(
            select(TestResultBugSnapshot)
            .where(TestResultBugSnapshot.testing_id == 1001)
            .order_by(TestResultBugSnapshot.snapshot_date)
        ).all()

        # 検出履歴(05-01 の検出2)は残り、完了は現在値(05-02 の Fixed2)へ移動する。
        self.assertEqual([row.snapshot_date.isoformat() for row in rows], ["2026-05-01", "2026-05-02"])
        self.assertEqual(
            [(row.detected_count, row.suspend_count, row.fixed_count) for row in rows],
            [(2, 0, 0), (0, 0, 2)],
        )

    def test_replace_progress_detected_high_water_does_not_double_count(self):
        # 同じデータを再取込しても検出は二重計上されない。
        replace_progress(self.db, make_payload(testing_id=1001, pass_count=4))
        replace_progress(self.db, make_payload(testing_id=1001, pass_count=4))

        rows = self.db.scalars(
            select(TestResultBugSnapshot).where(TestResultBugSnapshot.testing_id == 1001)
        ).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].detected_count, rows[0].suspend_count, rows[0].fixed_count), (2, 0, 1))

        # 不具合が消えても（Fail0/Fixed0）、検出累積(ハイウォーターマーク)は減らさない。
        lower = make_payload(testing_id=1001, pass_count=6)
        lower.files[0].daily[0].fail = 0
        lower.files[0].daily[0].fixed = 0
        replace_progress(self.db, lower)

        rows = self.db.scalars(
            select(TestResultBugSnapshot).where(TestResultBugSnapshot.testing_id == 1001)
        ).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].detected_count, rows[0].suspend_count, rows[0].fixed_count), (2, 0, 0))

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
