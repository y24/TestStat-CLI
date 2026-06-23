import os
import sys
import unittest

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: F401
from app.crud.setting import (  # noqa: E402
    get_bug_state_color_settings,
    update_bug_state_color_settings,
    get_pb_chart_settings,
    get_progress_status_thresholds,
    update_pb_chart_settings,
    update_progress_status_thresholds,
)
from app.database import Base  # noqa: E402
from app.schemas.setting import (  # noqa: E402
    BugStateColorSetting,
    BugStateColorSettings,
    PbChartSettings,
    ProgressStatusThresholds,
)


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return Session()


class TestSettingCRUD(unittest.TestCase):
    def setUp(self):
        self.db = make_session()

    def tearDown(self):
        self.db.close()

    def test_get_progress_status_thresholds_returns_defaults(self):
        thresholds = get_progress_status_thresholds(self.db)

        self.assertEqual(thresholds.caution, 90)
        self.assertEqual(thresholds.warning, 60)

    def test_update_progress_status_thresholds_persists_values(self):
        update_progress_status_thresholds(
            self.db,
            ProgressStatusThresholds(caution=95, warning=60),
        )

        thresholds = get_progress_status_thresholds(self.db)
        self.assertEqual(thresholds.caution, 95)
        self.assertEqual(thresholds.warning, 60)

    def test_get_pb_chart_settings_returns_defaults(self):
        settings = get_pb_chart_settings(self.db)

        self.assertEqual(settings.bug_axis_max, 30)

    def test_update_pb_chart_settings_persists_values(self):
        update_pb_chart_settings(self.db, PbChartSettings(bug_axis_max=80))

        settings = get_pb_chart_settings(self.db)
        self.assertEqual(settings.bug_axis_max, 80)

    def test_get_bug_state_color_settings_returns_defaults(self):
        settings = get_bug_state_color_settings(self.db)

        self.assertEqual([item.state for item in settings.items], [
            "New",
            "In Progress",
            "Dev In Progress",
            "Resolved",
            "Done",
            "Suspend",
        ])
        self.assertEqual(settings.items[0].background_color, "#f7f9fb")

    def test_update_bug_state_color_settings_persists_values(self):
        update_bug_state_color_settings(
            self.db,
            BugStateColorSettings(
                items=[
                    BugStateColorSetting(
                        state="Active",
                        background_color="#eef9ff",
                        text_color="#0369a1",
                        border_color="#bae6fd",
                    ),
                    BugStateColorSetting(
                        state="Closed",
                        background_color="#edf8f3",
                        text_color="#147d54",
                        border_color="#bfdacb",
                    ),
                ]
            ),
        )

        settings = get_bug_state_color_settings(self.db)
        self.assertEqual([item.state for item in settings.items], ["Active", "Closed"])
        self.assertEqual(settings.items[1].text_color, "#147d54")


if __name__ == "__main__":
    unittest.main()

