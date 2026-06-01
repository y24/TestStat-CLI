import os
import sys
import unittest
from datetime import date

SERVER_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.services.azure_devops as ado  # noqa: E402
from app.config import Settings  # noqa: E402
from app.routers.azure_devops import router as azure_devops_router  # noqa: E402


def make_settings(**overrides) -> Settings:
    # 実環境の AZURE_DEVOPS_* / .env に左右されないよう明示的に指定する。
    values = {
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "AZURE_DEVOPS_USE_MOCK": False,
        "AZURE_DEVOPS_PAT": "dummy-pat",
        "AZURE_DEVOPS_ORGANIZATION": "my-org",
        "AZURE_DEVOPS_PROJECT": "",
        "AZURE_DEVOPS_API_VERSION": "7.1",
        "AZURE_DEVOPS_TITLE_FIELD": "System.Title",
        "AZURE_DEVOPS_START_DATE_FIELD": "Microsoft.VSTS.Scheduling.StartDate",
        "AZURE_DEVOPS_END_DATE_FIELD": "Microsoft.VSTS.Scheduling.FinishDate",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class TestMockMode(unittest.TestCase):
    def test_returns_mock_work_item(self):
        settings = make_settings(AZURE_DEVOPS_USE_MOCK=True)
        info = ado.fetch_work_item(1001, settings)
        self.assertEqual(info.work_item_id, 1001)
        self.assertIn("1001", info.name)
        self.assertEqual(info.start_date, date(2026, 5, 1))
        self.assertEqual(info.end_date, date(2026, 6, 30))

    def test_non_positive_id_is_not_found(self):
        settings = make_settings(AZURE_DEVOPS_USE_MOCK=True)
        with self.assertRaises(ado.WorkItemNotFound):
            ado.fetch_work_item(0, settings)


class TestRemoteMode(unittest.TestCase):
    """実 API は叩けないため、httpx.MockTransport で実接続パスを検証する。"""

    def _install_transport(self, handler):
        transport = httpx.MockTransport(handler)
        original = ado._build_client
        ado._build_client = lambda: httpx.Client(transport=transport, timeout=10.0)
        self.addCleanup(lambda: setattr(ado, "_build_client", original))

    def test_extracts_title_and_dates(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("authorization")
            return httpx.Response(
                200,
                json={
                    "id": 12,
                    "fields": {
                        "System.Title": "サンプルプロジェクト",
                        "Microsoft.VSTS.Scheduling.StartDate": "2026-05-01T00:00:00Z",
                        "Microsoft.VSTS.Scheduling.FinishDate": "2026-06-30T00:00:00.000Z",
                    },
                },
            )

        self._install_transport(handler)
        info = ado.fetch_work_item(12, make_settings())

        self.assertEqual(info.name, "サンプルプロジェクト")
        self.assertEqual(info.start_date, date(2026, 5, 1))
        self.assertEqual(info.end_date, date(2026, 6, 30))
        self.assertIn("dev.azure.com/my-org/_apis/wit/workitems/12", captured["url"])
        self.assertIn("api-version=7.1", captured["url"])
        self.assertIn("fields=", captured["url"])
        self.assertTrue(captured["auth"].startswith("Basic "))

    def test_uses_project_and_custom_fields(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return httpx.Response(
                200,
                json={
                    "id": 5,
                    "fields": {
                        "System.Title": "T",
                        "Custom.ActualStartDate": "2026-01-10T00:00:00Z",
                        "Custom.ActualEndDate": "2026-02-20T00:00:00Z",
                    },
                },
            )

        self._install_transport(handler)
        settings = make_settings(
            AZURE_DEVOPS_PROJECT="MyProject",
            AZURE_DEVOPS_START_DATE_FIELD="Custom.ActualStartDate",
            AZURE_DEVOPS_END_DATE_FIELD="Custom.ActualEndDate",
        )
        info = ado.fetch_work_item(5, settings)

        self.assertEqual(info.start_date, date(2026, 1, 10))
        self.assertEqual(info.end_date, date(2026, 2, 20))
        self.assertIn("dev.azure.com/my-org/MyProject/_apis/wit/workitems/5", captured["url"])

    def test_missing_date_fields_become_none(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"id": 7, "fields": {"System.Title": "T"}})

        self._install_transport(handler)
        info = ado.fetch_work_item(7, make_settings())
        self.assertEqual(info.name, "T")
        self.assertIsNone(info.start_date)
        self.assertIsNone(info.end_date)

    def test_404_raises_not_found(self):
        self._install_transport(lambda request: httpx.Response(404, json={}))
        with self.assertRaises(ado.WorkItemNotFound):
            ado.fetch_work_item(999, make_settings())

    def test_401_raises_auth_error(self):
        self._install_transport(lambda request: httpx.Response(401, text="unauthorized"))
        with self.assertRaises(ado.AzureDevOpsAuthError):
            ado.fetch_work_item(1, make_settings())

    def test_500_raises_generic_error(self):
        self._install_transport(lambda request: httpx.Response(500, text="boom"))
        with self.assertRaises(ado.AzureDevOpsError):
            ado.fetch_work_item(1, make_settings())

    def test_timeout_raises_generic_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timeout", request=request)

        self._install_transport(handler)
        with self.assertRaises(ado.AzureDevOpsError):
            ado.fetch_work_item(1, make_settings())

    def test_missing_config_raises_not_configured(self):
        settings = make_settings(AZURE_DEVOPS_PAT="", AZURE_DEVOPS_ORGANIZATION="")
        with self.assertRaises(ado.AzureDevOpsNotConfigured):
            ado.fetch_work_item(1, settings)


class TestRouterMapping(unittest.TestCase):
    """例外 → HTTP ステータスのマッピングを検証する。"""

    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(azure_devops_router)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self._original = ado.fetch_work_item

    def tearDown(self):
        import app.routers.azure_devops as router_mod

        router_mod.fetch_work_item = self._original

    def _patch(self, fn):
        import app.routers.azure_devops as router_mod

        router_mod.fetch_work_item = fn

    def test_success_returns_payload(self):
        self._patch(lambda wid: ado.WorkItemInfo(wid, "名前", date(2026, 5, 1), date(2026, 6, 30)))
        res = self.client.get("/api/v1/azure-devops/work-items/12")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(),
            {
                "work_item_id": 12,
                "name": "名前",
                "start_date": "2026-05-01",
                "end_date": "2026-06-30",
            },
        )

    def test_not_found_maps_to_404(self):
        def raise_not_found(wid):
            raise ado.WorkItemNotFound()

        self._patch(raise_not_found)
        self.assertEqual(self.client.get("/api/v1/azure-devops/work-items/9").status_code, 404)

    def test_not_configured_maps_to_503(self):
        def raise_not_configured(wid):
            raise ado.AzureDevOpsNotConfigured()

        self._patch(raise_not_configured)
        self.assertEqual(self.client.get("/api/v1/azure-devops/work-items/9").status_code, 503)

    def test_auth_error_maps_to_502(self):
        def raise_auth(wid):
            raise ado.AzureDevOpsAuthError()

        self._patch(raise_auth)
        self.assertEqual(self.client.get("/api/v1/azure-devops/work-items/9").status_code, 502)


if __name__ == "__main__":
    unittest.main()
