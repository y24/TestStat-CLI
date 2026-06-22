import unittest
from unittest.mock import patch

from utils.ApiIntegration import update_subtask_progress


class ApiIntegrationTests(unittest.TestCase):
    def test_update_subtask_progress_appends_subtasks_path_to_base_url(self):
        requests = []

        class FakeResponse:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(req):
            requests.append(req)
            return FakeResponse()

        with patch("utils.ApiIntegration.urllib.request.urlopen", side_effect=fake_urlopen):
            success, msg = update_subtask_progress("http://localhost:5173/api", 123, 85)

        self.assertTrue(success)
        self.assertEqual(msg, "")
        self.assertEqual(requests[0].full_url, "http://localhost:5173/api/subtasks/123")

    def test_update_subtask_progress_handles_trailing_slash(self):
        requests = []

        class FakeResponse:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(req):
            requests.append(req)
            return FakeResponse()

        with patch("utils.ApiIntegration.urllib.request.urlopen", side_effect=fake_urlopen):
            success, _ = update_subtask_progress("http://localhost:5173/api/", 123, 85)

        self.assertTrue(success)
        self.assertEqual(requests[0].full_url, "http://localhost:5173/api/subtasks/123")


if __name__ == "__main__":
    unittest.main()
