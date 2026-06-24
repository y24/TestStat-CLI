import os
import sys
import unittest
from datetime import date, datetime

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: F401,E402
import app.services.azure_devops as ado  # noqa: E402
from app.config import Settings  # noqa: E402
from app.crud.bug import (  # noqa: E402
    build_work_item_url,
    delete_bug_count_data,
    get_bug_cumulative,
    get_open_bugs,
    replace_bugs,
)
from app.crud.pb_chart import get_pb_chart  # noqa: E402
from app.crud.project import create_project  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.progress import TestResultBugSnapshot, Testing  # noqa: E402
from app.schemas.project import ProjectCreate  # noqa: E402
from app.services.azure_devops import BugWorkItem  # noqa: E402


def make_settings(**overrides) -> Settings:
    values = {
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "AZURE_DEVOPS_USE_MOCK": False,
        "AZURE_DEVOPS_PAT": "dummy-pat",
        "AZURE_DEVOPS_ORGANIZATION": "my-org",
        "AZURE_DEVOPS_PROJECT": "",
        "AZURE_DEVOPS_API_VERSION": "7.1",
        "AZURE_DEVOPS_TITLE_FIELD": "System.Title",
        "AZURE_DEVOPS_BUG_WIT": "Bug",
        "AZURE_DEVOPS_BUG_IGNORE_STATUS": "Removed",
        "AZURE_DEVOPS_BUG_SUSPEND_STATUS": "Suspend",
        "AZURE_DEVOPS_BUG_CREATED_DATE_FIELD": "System.CreatedDate",
        "AZURE_DEVOPS_BUG_FINISH_DATE_FIELD": "Microsoft.VSTS.Common.ClosedDate",
        "AZURE_DEVOPS_BUG_STATE_FIELD": "System.State",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_fk(conn, _):
        conn.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


class TestSettingsParsing(unittest.TestCase):
    def test_ignore_and_suspend_sets(self):
        s = make_settings(
            AZURE_DEVOPS_BUG_IGNORE_STATUS="Removed, Done",
            AZURE_DEVOPS_BUG_SUSPEND_STATUS="Suspend , Hold",
        )
        self.assertEqual(s.azure_devops_bug_ignore_status_set, {"Removed", "Done"})
        self.assertEqual(s.azure_devops_bug_suspend_status_set, {"Suspend", "Hold"})

    def test_ignore_wins_over_suspend(self):
        s = make_settings(
            AZURE_DEVOPS_BUG_IGNORE_STATUS="Removed,Suspend",
            AZURE_DEVOPS_BUG_SUSPEND_STATUS="Suspend",
        )
        self.assertEqual(s.azure_devops_bug_suspend_status_set, set())

    def test_bug_date_fields_are_ordered_csv_lists(self):
        s = make_settings(
            AZURE_DEVOPS_BUG_CREATED_DATE_FIELD=" System.CreatedDate, Custom.CreatedDate, System.CreatedDate ",
            AZURE_DEVOPS_BUG_FINISH_DATE_FIELD="Microsoft.VSTS.Common.ClosedDate, Custom.FinishDate",
        )
        self.assertEqual(
            s.azure_devops_bug_created_date_fields,
            ["System.CreatedDate", "Custom.CreatedDate"],
        )
        self.assertEqual(
            s.azure_devops_bug_finish_date_fields,
            ["Microsoft.VSTS.Common.ClosedDate", "Custom.FinishDate"],
        )


class TestMockMode(unittest.TestCase):
    def test_returns_bugs_without_removed(self):
        settings = make_settings(AZURE_DEVOPS_USE_MOCK=True)
        bugs = ado.fetch_child_bugs(1001, settings)
        states = [b.state for b in bugs]
        self.assertNotIn("Removed", states)
        self.assertIn("Suspend", states)  # Suspend は残る
        self.assertTrue(all(isinstance(b, BugWorkItem) for b in bugs))

    def test_non_positive_id_not_found(self):
        settings = make_settings(AZURE_DEVOPS_USE_MOCK=True)
        with self.assertRaises(ado.WorkItemNotFound):
            ado.fetch_child_bugs(0, settings)


class TestRemoteMode(unittest.TestCase):
    def _install_transport(self, handler):
        transport = httpx.MockTransport(handler)
        original = ado._build_client
        ado._build_client = lambda: httpx.Client(transport=transport, timeout=10.0)
        self.addCleanup(lambda: setattr(ado, "_build_client", original))

    def test_wiql_then_fields(self):
        captured = {"requests": []}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["requests"].append((request.method, str(request.url)))
            if request.url.path.endswith("/wiql"):
                return httpx.Response(200, json={"workItems": [{"id": 9001}, {"id": 9002}]})
            return httpx.Response(
                200,
                json={
                    "count": 2,
                    "value": [
                        {"id": 9001, "fields": {
                            "System.Title": "A", "System.State": "Closed",
                            "System.CreatedDate": "2026-05-02T09:00:00Z",
                            "Microsoft.VSTS.Common.ClosedDate": "2026-05-06T10:00:00Z"}},
                        {"id": 9002, "fields": {
                            "System.Title": "B", "System.State": "Active",
                            "System.CreatedDate": "2026-05-03T09:00:00Z"}},
                    ],
                },
            )

        self._install_transport(handler)
        bugs = ado.fetch_child_bugs(1001, make_settings())

        self.assertEqual(len(bugs), 2)
        self.assertEqual(bugs[0].created_date, date(2026, 5, 2))
        self.assertEqual(bugs[0].finish_date, date(2026, 5, 6))
        self.assertIsNone(bugs[1].finish_date)
        self.assertEqual(captured["requests"][0][0], "POST")
        self.assertTrue(captured["requests"][0][1].endswith("/wiql?api-version=7.1"))

    def test_project_specific_work_item_type_and_tag_are_used_in_wiql(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/wiql"):
                captured["body"] = request.read().decode("utf-8")
                return httpx.Response(200, json={"workItems": []})
            return httpx.Response(200, json={"value": []})

        self._install_transport(handler)
        bugs = ado.fetch_child_bugs(2002, make_settings(), bug_work_item_type="不具合", bug_tag="Release-A")

        self.assertEqual(bugs, [])
        self.assertIn("[System.Parent] = 2002", captured["body"])
        self.assertIn("[System.WorkItemType] = '不具合'", captured["body"])
        self.assertIn("[System.Tags] Contains 'Release-A'", captured["body"])

    def test_bug_date_fields_fallback_in_order(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/wiql"):
                return httpx.Response(200, json={"workItems": [{"id": 9001}]})
            captured["fields"] = request.url.params.get("fields")
            return httpx.Response(200, json={"value": [
                {"id": 9001, "fields": {
                    "System.Title": "A",
                    "System.State": "Closed",
                    "Microsoft.VSTS.Scheduling.StartDate": "2026-05-02T09:00:00Z",
                    "Custom.FinishDate": "2026-05-06T10:00:00Z",
                }},
            ]})

        self._install_transport(handler)
        settings = make_settings(
            AZURE_DEVOPS_BUG_CREATED_DATE_FIELD="System.CreatedDate,Microsoft.VSTS.Scheduling.StartDate",
            AZURE_DEVOPS_BUG_FINISH_DATE_FIELD="Microsoft.VSTS.Common.ClosedDate,Custom.FinishDate",
        )
        bugs = ado.fetch_child_bugs(1001, settings)

        self.assertEqual(bugs[0].created_date, date(2026, 5, 2))
        self.assertEqual(bugs[0].finish_date, date(2026, 5, 6))
        self.assertEqual(
            captured["fields"],
            "System.Title,System.State,System.CreatedDate,Microsoft.VSTS.Scheduling.StartDate,"
            "Microsoft.VSTS.Common.ClosedDate,Custom.FinishDate",
        )

    def test_ignore_status_filtered_remote(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/wiql"):
                return httpx.Response(200, json={"workItems": [{"id": 1}, {"id": 2}]})
            return httpx.Response(200, json={"value": [
                {"id": 1, "fields": {"System.State": "Removed"}},
                {"id": 2, "fields": {"System.State": "Active",
                                     "System.CreatedDate": "2026-05-01T00:00:00Z"}},
            ]})

        self._install_transport(handler)
        bugs = ado.fetch_child_bugs(1001, make_settings())
        self.assertEqual([b.work_item_id for b in bugs], [2])

    def test_empty_wiql_skips_fields_call(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(200, json={"workItems": []})

        self._install_transport(handler)
        bugs = ado.fetch_child_bugs(1001, make_settings())
        self.assertEqual(bugs, [])
        self.assertEqual(calls["n"], 1)  # WIQL のみ

    def test_404_raises_not_found(self):
        self._install_transport(lambda r: httpx.Response(404, json={}))
        with self.assertRaises(ado.WorkItemNotFound):
            ado.fetch_child_bugs(1001, make_settings())


class TestCrud(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        create_project(self.db, ProjectCreate(testing_id=1001, name="P"))

    def _bugs(self):
        return [
            BugWorkItem(9001, "a", "Closed", date(2026, 5, 2), date(2026, 5, 6)),
            BugWorkItem(9002, "b", "Active", date(2026, 5, 3), None),
            BugWorkItem(9007, "c", "Suspend", date(2026, 5, 7), date(2026, 5, 11)),
        ]

    def test_replace_counts(self):
        res = replace_bugs(self.db, 1001, self._bugs(), {"Suspend"}, datetime(2026, 5, 20, 12, 0))
        self.assertEqual(res.fetched, 3)
        self.assertEqual(res.open_count, 1)
        self.assertEqual(res.suspended_count, 1)
        self.assertEqual(res.resolved_count, 1)

    def test_suspend_status_counts_as_suspended_without_finish_date(self):
        bugs = [
            BugWorkItem(9001, "open", "Active", date(2026, 5, 2), None),
            BugWorkItem(9002, "suspend", "Suspend", date(2026, 5, 3), None),
        ]
        res = replace_bugs(self.db, 1001, bugs, {"Suspend"}, datetime(2026, 5, 20, 12, 0))
        self.assertEqual((res.open_count, res.suspended_count, res.resolved_count), (1, 1, 0))
        cum = get_bug_cumulative(self.db, 1001, [date(2026, 5, 20)], {"Suspend"})
        self.assertEqual(cum[date(2026, 5, 20)], (1, 1, 0))

    def test_replace_is_idempotent(self):
        replace_bugs(self.db, 1001, self._bugs(), {"Suspend"}, datetime(2026, 5, 20, 12, 0))
        replace_bugs(self.db, 1001, self._bugs(), {"Suspend"}, datetime(2026, 5, 21, 12, 0))
        cum = get_bug_cumulative(self.db, 1001, [date(2026, 5, 20)], {"Suspend"})
        # 検出累積=3（重複していない）
        o, s, r = cum[date(2026, 5, 20)]
        self.assertEqual((o, s, r), (1, 1, 1))

    def test_cumulative_boundaries(self):
        replace_bugs(self.db, 1001, self._bugs(), {"Suspend"}, datetime(2026, 5, 20, 12, 0))
        cum = get_bug_cumulative(
            self.db, 1001,
            [date(2026, 5, 1), date(2026, 5, 6), date(2026, 5, 11), date(2026, 5, 20)],
            {"Suspend"},
        )
        self.assertEqual(cum[date(2026, 5, 1)], (0, 0, 0))     # 起票前
        self.assertEqual(cum[date(2026, 5, 6)], (1, 0, 1))     # 9001 完了当日
        self.assertEqual(cum[date(2026, 5, 11)], (1, 1, 1))    # 9007 見送り当日
        self.assertEqual(cum[date(2026, 5, 20)], (1, 1, 1))

    def test_get_open_bugs_returns_unfinished_with_links(self):
        replace_bugs(self.db, 1001, self._bugs(), {"Suspend"}, datetime(2026, 5, 20, 12, 0))
        bugs = get_open_bugs(
            self.db,
            1001,
            make_settings(AZURE_DEVOPS_ORGANIZATION="my-org", AZURE_DEVOPS_PROJECT="my-project"),
            {"Suspend"},
        )
        self.assertEqual([bug.work_item_id for bug in bugs], [9002, 9007])
        self.assertEqual(bugs[0].title, "b")
        self.assertEqual(bugs[0].state, "Active")
        self.assertFalse(bugs[0].is_suspended)
        self.assertEqual(bugs[0].url, "https://dev.azure.com/my-org/my-project/_workitems/edit/9002")
        self.assertEqual(bugs[1].state, "Suspend")
        self.assertTrue(bugs[1].is_suspended)

    def test_build_work_item_url_without_organization(self):
        self.assertIsNone(build_work_item_url(9002, make_settings(AZURE_DEVOPS_ORGANIZATION="")))

    def test_delete_bug_count_data_removes_all_bug_sources(self):
        replace_bugs(self.db, 1001, self._bugs(), {"Suspend"}, datetime(2026, 5, 20, 12, 0))
        self.db.add(Testing(testing_id=1001, project_name="P"))
        self.db.commit()
        self.db.add(
            TestResultBugSnapshot(
                testing_id=1001,
                label=None,
                snapshot_date=date(2026, 5, 20),
                detected_count=2,
                suspend_count=1,
                fixed_count=0,
                sent_at=datetime(2026, 5, 20, 12, 0),
            )
        )
        self.db.commit()

        self.assertEqual(delete_bug_count_data(self.db, 1001), (3, 1))
        cum = get_bug_cumulative(self.db, 1001, [date(2026, 5, 20)], {"Suspend"})
        self.assertEqual(cum[date(2026, 5, 20)], (0, 0, 0))


class TestPbChartIntegration(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        create_project(self.db, ProjectCreate(testing_id=1001, name="P"))
        # get_pb_chart は get_settings() で suspend states を読む。テストでは Suspend を有効化。
        import app.crud.pb_chart as pb_mod
        self._original_settings = pb_mod.get_settings
        pb_mod.get_settings = lambda: make_settings(AZURE_DEVOPS_BUG_SUSPEND_STATUS="Suspend")

    def tearDown(self):
        import app.crud.pb_chart as pb_mod
        pb_mod.get_settings = self._original_settings

    def test_no_bugs(self):
        replace_bugs(self.db, 1001, [], {"Suspend"}, datetime(2026, 5, 20, 12, 0))
        chart = get_pb_chart(self.db, 1001)
        self.assertFalse(chart.has_bugs)

    def test_bugs_only_builds_range_and_series(self):
        bugs = [
            BugWorkItem(9001, "a", "Closed", date(2026, 5, 2), date(2026, 5, 6)),
            BugWorkItem(9007, "c", "Suspend", date(2026, 5, 7), date(2026, 5, 11)),
            BugWorkItem(9002, "b", "Active", date(2026, 5, 10), None),
        ]
        replace_bugs(self.db, 1001, bugs, {"Suspend"}, datetime(2026, 5, 20, 12, 0))
        chart = get_pb_chart(self.db, 1001)
        self.assertTrue(chart.has_bugs)
        self.assertIsNotNone(chart.range)
        self.assertEqual(chart.range["from"], "2026-05-02")
        self.assertEqual(chart.range["to"], "2026-05-11")
        last = chart.series[-1]
        self.assertEqual((last.bug_open, last.bug_suspended, last.bug_resolved), (1, 1, 1))


class TestRouter(unittest.TestCase):
    def setUp(self):
        from app.database import get_db
        from app.routers.bug import router as bug_router

        self.db = make_session()
        create_project(self.db, ProjectCreate(testing_id=1001, name="P"))

        self.app = FastAPI()
        self.app.include_router(bug_router)
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(self.app, raise_server_exceptions=False)

        import app.routers.bug as bug_mod
        self._original_fetch = bug_mod.fetch_child_bugs
        self._original_settings = bug_mod.get_settings
        bug_mod.get_settings = lambda: make_settings(AZURE_DEVOPS_BUG_SUSPEND_STATUS="Suspend")

    def tearDown(self):
        import app.routers.bug as bug_mod
        bug_mod.fetch_child_bugs = self._original_fetch
        bug_mod.get_settings = self._original_settings

    def _patch_fetch(self, fn):
        import app.routers.bug as bug_mod
        bug_mod.fetch_child_bugs = fn

    def test_success(self):
        self._patch_fetch(lambda wid, *args, **kwargs: [
            BugWorkItem(9001, "a", "Closed", date(2026, 5, 2), date(2026, 5, 6)),
            BugWorkItem(9007, "c", "Suspend", date(2026, 5, 7), date(2026, 5, 11)),
        ])
        res = self.client.post("/api/v1/projects/1001/bugs/sync")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["fetched"], 2)
        self.assertEqual(body["resolved_count"], 1)
        self.assertEqual(body["suspended_count"], 1)

    def test_sync_uses_project_specific_azure_bug_settings(self):
        from app.crud.project import update_project
        from app.schemas.project import ProjectUpdate

        update_project(
            self.db,
            1001,
            ProjectUpdate(
                bug_parent_work_item_id=2002,
                bug_work_item_type="不具合",
                bug_tag="Release-A",
            ),
        )
        captured = {}

        def fake_fetch(wid, settings=None, **kwargs):
            captured["wid"] = wid
            captured.update(kwargs)
            return [BugWorkItem(9002, "open", "Active", date(2026, 5, 3), None)]

        self._patch_fetch(fake_fetch)
        res = self.client.post("/api/v1/projects/1001/bugs/sync")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(captured, {
            "wid": 2002,
            "bug_work_item_type": "不具合",
            "bug_tag": "Release-A",
        })

    def test_unknown_project_404(self):
        self._patch_fetch(lambda wid, *args, **kwargs: [])
        self.assertEqual(self.client.post("/api/v1/projects/9999/bugs/sync").status_code, 404)

    def test_delete_bug_count_data(self):
        self._patch_fetch(lambda wid, *args, **kwargs: [
            BugWorkItem(9002, "open", "Active", date(2026, 5, 3), None),
        ])
        self.assertEqual(self.client.post("/api/v1/projects/1001/bugs/sync").status_code, 200)
        self.assertEqual(self.client.delete("/api/v1/projects/1001/bugs").status_code, 204)
        res = self.client.get("/api/v1/projects/1001/bugs/open")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_delete_bug_count_data_unknown_project_404(self):
        self.assertEqual(self.client.delete("/api/v1/projects/9999/bugs").status_code, 404)

    def test_not_configured_503(self):
        def raise_nc(wid, *args, **kwargs):
            raise ado.AzureDevOpsNotConfigured()

        self._patch_fetch(raise_nc)
        self.assertEqual(self.client.post("/api/v1/projects/1001/bugs/sync").status_code, 503)

    def test_parent_not_found_404(self):
        def raise_nf(wid, *args, **kwargs):
            raise ado.WorkItemNotFound()

        self._patch_fetch(raise_nf)
        self.assertEqual(self.client.post("/api/v1/projects/1001/bugs/sync").status_code, 404)

    def test_list_open_bugs(self):
        self._patch_fetch(
            lambda wid, *args, **kwargs: [
                BugWorkItem(9001, "done", "Closed", date(2026, 5, 2), date(2026, 5, 6)),
                BugWorkItem(9002, "open", "Active", date(2026, 5, 3), None),
                BugWorkItem(9003, "suspend", "Suspend", date(2026, 5, 4), None),
                BugWorkItem(9004, "finished suspend", "Suspend", date(2026, 5, 5), date(2026, 5, 8)),
            ]
        )
        self.assertEqual(self.client.post("/api/v1/projects/1001/bugs/sync").status_code, 200)
        res = self.client.get("/api/v1/projects/1001/bugs/open")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual([item["work_item_id"] for item in body], [9002, 9003, 9004])
        self.assertEqual(body[0]["title"], "open")
        self.assertEqual(body[0]["state"], "Active")
        self.assertFalse(body[0]["is_suspended"])
        self.assertEqual(body[0]["url"], "https://dev.azure.com/my-org/_workitems/edit/9002")
        self.assertEqual(body[1]["state"], "Suspend")
        self.assertTrue(body[1]["is_suspended"])
        self.assertEqual(body[2]["title"], "finished suspend")
        self.assertTrue(body[2]["is_suspended"])

    def test_mock_sync_exposes_suspended_bug_in_list(self):
        self._patch_fetch(self._original_fetch)
        res = self.client.post("/api/v1/projects/1001/bugs/sync")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertGreaterEqual(body["suspended_count"], 1)

        list_res = self.client.get("/api/v1/projects/1001/bugs/open")
        self.assertEqual(list_res.status_code, 200)
        suspended = [item for item in list_res.json() if item["is_suspended"]]
        self.assertTrue(any(item["work_item_id"] == 9009 for item in suspended))
        self.assertTrue(any(item["work_item_id"] == 9007 for item in suspended))
        self.assertTrue(any(item["work_item_id"] == 9008 for item in suspended))
        self.assertTrue(all(item["state"] == "Suspend" for item in suspended))

    def test_list_open_bugs_fetches_azure_devops_in_test_result_mode(self):
        from app.crud.project import update_project
        from app.schemas.project import ProjectUpdate

        update_project(self.db, 1001, ProjectUpdate(bug_count_source="test_result"))
        self._patch_fetch(
            lambda wid, settings=None, **kwargs: [
                BugWorkItem(9001, "done", "Closed", date(2026, 5, 2), date(2026, 5, 6)),
                BugWorkItem(9002, "open", "Active", date(2026, 5, 3), None),
                BugWorkItem(9003, "suspend", "Suspend", date(2026, 5, 4), None),
                BugWorkItem(9004, "finished suspend", "Suspend", date(2026, 5, 5), date(2026, 5, 8)),
            ]
        )

        res = self.client.get("/api/v1/projects/1001/bugs/open")

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual([item["work_item_id"] for item in body], [9002, 9003, 9004])
        self.assertFalse(body[0]["is_suspended"])
        self.assertTrue(body[1]["is_suspended"])
        self.assertTrue(body[2]["is_suspended"])


if __name__ == "__main__":
    unittest.main()


