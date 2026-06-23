import unittest
import urllib.error
from unittest.mock import patch

from utils.ReportingClient import build_progress_payload, send_progress


class FakeResponse:
    def __init__(self, status=200, body="{}"):
        self.status = status
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ReportingClientPayloadTests(unittest.TestCase):
    def test_build_progress_payload_expands_daily_and_person_rows(self):
        project_info = {"testing_id": 1001, "project_name": "Sample"}
        results = [
            (
                r"C:\work\sample1.xlsx",
                {
                    "label": "TEST001",
                    "target_environments": ["env-a"],
                    "stats": {
                        "all": 10,
                        "available": 8,
                        "excluded": 2,
                        "completed": 5,
                        "executed": 6,
                        "incompleted": 2,
                    },
                    "total": {
                        "Pass": 4,
                        "Fixed": 1,
                        "Fail": 1,
                        "Blocked": 0,
                        "Suspend": 0,
                        "N/A": 0,
                        "未実施": 2,
                        "完了数": 5,
                        "消化数": 6,
                    },
                    "run": {"start_date": "2026-05-01", "last_update": "2026-05-02"},
                    "daily": {
                        "2026-05-01": {
                            "Pass": 3,
                            "Fixed": 1,
                            "Fail": 1,
                            "完了数": 4,
                            "消化数": 5,
                            "計画数": 7,
                        }
                    },
                    "by_name": {"2026-05-01": {"Alice": 3, "Bob": 2, "": 1}},
                    "source_url": "https://contoso.sharepoint.com/:x:/s/site/Eabc",
                },
            )
        ]

        payload = build_progress_payload(project_info, results, sender="sender-a")

        self.assertEqual(payload["testing_id"], 1001)
        self.assertEqual(payload["project_name"], "Sample")
        self.assertEqual(payload["sender"], "sender-a")
        self.assertEqual(len(payload["files"]), 1)

        file_payload = payload["files"][0]
        self.assertEqual(file_payload["file_name"], "sample1.xlsx")
        self.assertEqual(file_payload["environment"], "env-a")
        self.assertEqual(file_payload["source_url"], "https://contoso.sharepoint.com/:x:/s/site/Eabc")
        self.assertEqual(file_payload["available_cases"], 8)
        self.assertEqual(file_payload["completed_rate"], 62.5)
        self.assertEqual(file_payload["executed_rate"], 75.0)
        self.assertEqual(file_payload["results"]["Pass"], 4)
        self.assertEqual(file_payload["daily"][0]["planned"], 7)
        self.assertEqual(
            file_payload["by_person"],
            [
                {"date": "2026-05-01", "person": "Alice", "count": 3},
                {"date": "2026-05-01", "person": "Bob", "count": 2},
            ],
        )

    def test_build_progress_payload_preserves_error_files_for_server_validation(self):
        project_info = {"testing_id": 1001, "project_name": "Sample"}
        results = [
            (
                "missing.xlsx",
                {
                    "label": "TEST999",
                    "source_url": "https://contoso.sharepoint.com/:x:/s/site/E999",
                    "error": {"type": "sheet_not_found", "message": "sheet missing"},
                },
            )
        ]

        payload = build_progress_payload(project_info, results)

        self.assertEqual(payload["files"][0]["file_name"], "missing.xlsx")
        self.assertEqual(payload["files"][0]["source_url"], "https://contoso.sharepoint.com/:x:/s/site/E999")
        self.assertEqual(payload["files"][0]["available_cases"], 0)
        self.assertEqual(payload["files"][0]["error"], "sheet missing")


class ReportingClientSendTests(unittest.TestCase):
    def test_send_progress_skips_archived_project(self):
        requests = []

        def fake_urlopen(req, timeout=10):
            requests.append(req)
            return FakeResponse(body='{"testing_id":1001,"archived":true}')

        with patch("utils.ReportingClient.urllib.request.urlopen", side_effect=fake_urlopen):
            success, msg = send_progress("http://localhost:18000/api", {"testing_id": 1001, "files": []})

        self.assertFalse(success)
        self.assertIn("アーカイブ済み", msg)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].full_url, "http://localhost:18000/api/v1/projects/1001")

    def test_send_progress_posts_when_project_is_active(self):
        requests = []

        def fake_urlopen(req, timeout=10):
            requests.append(req)
            if req.full_url.endswith("/api/v1/projects/1001"):
                return FakeResponse(body='{"testing_id":1001,"archived":false}')
            return FakeResponse(body='{"testing_id":1001,"inserted_files":0,"inserted_daily_rows":0,"inserted_person_rows":0}')

        with patch("utils.ReportingClient.urllib.request.urlopen", side_effect=fake_urlopen):
            success, _ = send_progress("http://localhost:18000/api", {"testing_id": 1001, "files": []})

        self.assertTrue(success)
        self.assertEqual([req.full_url for req in requests], [
            "http://localhost:18000/api/v1/projects/1001",
            "http://localhost:18000/api/v1/progress",
        ])

    def test_send_progress_posts_when_project_is_not_registered(self):
        requests = []

        def fake_urlopen(req, timeout=10):
            requests.append(req)
            if req.full_url.endswith("/api/v1/projects/1001"):
                raise urllib.error.HTTPError(req.full_url, 404, "Not Found", hdrs=None, fp=None)
            return FakeResponse(body='{"testing_id":1001,"inserted_files":0,"inserted_daily_rows":0,"inserted_person_rows":0}')

        with patch("utils.ReportingClient.urllib.request.urlopen", side_effect=fake_urlopen):
            success, _ = send_progress("http://localhost:18000/api", {"testing_id": 1001, "files": []})

        self.assertTrue(success)
        self.assertEqual(len(requests), 2)


if __name__ == "__main__":
    unittest.main()
