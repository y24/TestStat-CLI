import json
import os
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from utils import RemoteSource
from utils.RemoteSource import (
    RemoteFileManager,
    RemoteSourceError,
    encode_share_id,
    is_remote_path,
    resolve_download_url,
)


class FakeResponse:
    def __init__(self, body="{}"):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class IsRemotePathTests(unittest.TestCase):
    def test_https_url_is_remote(self):
        self.assertTrue(is_remote_path("https://contoso.sharepoint.com/:x:/s/site/Eabc"))

    def test_http_url_is_remote(self):
        self.assertTrue(is_remote_path("http://example.com/file.xlsx"))

    def test_local_path_is_not_remote(self):
        self.assertFalse(is_remote_path("input_sample/sample1.xlsx"))
        self.assertFalse(is_remote_path("C:\\data\\sample.xlsx"))

    def test_non_string_is_not_remote(self):
        self.assertFalse(is_remote_path(None))


class EncodeShareIdTests(unittest.TestCase):
    def test_known_vector(self):
        # Microsoft 公式ドキュメントの例
        url = "https://onedrive.live.com/redir?resid=1!1&authkey=!1&e=1"
        self.assertEqual(
            encode_share_id(url),
            "u!aHR0cHM6Ly9vbmVkcml2ZS5saXZlLmNvbS9yZWRpcj9yZXNpZD0xITEmYXV0aGtleT0hMSZlPTE",
        )

    def test_prefix_and_no_padding(self):
        share_id = encode_share_id("https://contoso.sharepoint.com/:x:/s/site/Eabc")
        self.assertTrue(share_id.startswith("u!"))
        self.assertNotIn("=", share_id)
        self.assertNotIn("/", share_id)
        self.assertNotIn("+", share_id)


class ResolveDownloadUrlTests(unittest.TestCase):
    def test_returns_name_and_download_url(self):
        body = json.dumps({
            "id": "abc",
            "name": "sample.xlsx",
            "@microsoft.graph.downloadUrl": "https://dl.example/abc",
        })
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["auth"] = req.get_header("Authorization")
            return FakeResponse(body)

        with patch("utils.RemoteSource.urllib.request.urlopen", side_effect=fake_urlopen):
            name, url = resolve_download_url("u!xxx", "tok", timeout=5)

        self.assertEqual(name, "sample.xlsx")
        self.assertEqual(url, "https://dl.example/abc")
        self.assertIn("/shares/u!xxx/driveItem", captured["url"])
        self.assertEqual(captured["auth"], "Bearer tok")

    def test_403_raises_permission_message(self):
        err = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        with patch("utils.RemoteSource.urllib.request.urlopen", side_effect=err):
            with self.assertRaises(RemoteSourceError) as ctx:
                resolve_download_url("u!xxx", "tok")
        self.assertIn("403", str(ctx.exception))

    def test_404_raises_resolve_message(self):
        err = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
        with patch("utils.RemoteSource.urllib.request.urlopen", side_effect=err):
            with self.assertRaises(RemoteSourceError) as ctx:
                resolve_download_url("u!xxx", "tok")
        self.assertIn("404", str(ctx.exception))

    def test_missing_download_url_raises(self):
        body = json.dumps({"name": "sample.xlsx"})
        with patch("utils.RemoteSource.urllib.request.urlopen", return_value=FakeResponse(body)):
            with self.assertRaises(RemoteSourceError):
                resolve_download_url("u!xxx", "tok")


class GetAccessTokenTests(unittest.TestCase):
    def test_missing_az_raises(self):
        with patch("utils.RemoteSource.subprocess.run", side_effect=FileNotFoundError()):
            with self.assertRaises(RemoteSourceError) as ctx:
                RemoteSource.get_access_token()
        self.assertIn("Azure CLI", str(ctx.exception))

    def test_not_logged_in_raises(self):
        class Completed:
            returncode = 1
            stdout = ""
            stderr = "Please run 'az login' to setup account."

        with patch("utils.RemoteSource.subprocess.run", return_value=Completed()):
            with self.assertRaises(RemoteSourceError) as ctx:
                RemoteSource.get_access_token()
        self.assertIn("az login", str(ctx.exception))

    def test_returns_token(self):
        class Completed:
            returncode = 0
            stdout = "the-token\n"
            stderr = ""

        with patch("utils.RemoteSource.subprocess.run", return_value=Completed()):
            self.assertEqual(RemoteSource.get_access_token(), "the-token")


class RemoteFileManagerTests(unittest.TestCase):
    def test_mock_mode_copies_local_file(self):
        with tempfile.TemporaryDirectory() as src_dir:
            src = os.path.join(src_dir, "mock.xlsx")
            with open(src, "wb") as f:
                f.write(b"hello")

            mgr = RemoteFileManager({})
            try:
                with patch.dict(os.environ, {RemoteSource.MOCK_ENV_VAR: src}):
                    local = mgr.fetch("https://contoso.sharepoint.com/x")
                self.assertTrue(os.path.exists(local))
                self.assertEqual(os.path.basename(local), "mock.xlsx")
                with open(local, "rb") as f:
                    self.assertEqual(f.read(), b"hello")
            finally:
                mgr.cleanup()

    def test_same_url_is_cached(self):
        calls = []

        def fake_resolve(share_id, token, **kwargs):
            calls.append(share_id)
            return "sample.xlsx", "https://dl/x"

        def fake_download(url, name, temp_dir, **kwargs):
            path = os.path.join(temp_dir, name)
            with open(path, "wb") as f:
                f.write(b"x")
            return path

        mgr = RemoteFileManager({})
        try:
            with patch("utils.RemoteSource.get_access_token", return_value="tok"), \
                 patch("utils.RemoteSource.resolve_download_url", side_effect=fake_resolve), \
                 patch("utils.RemoteSource.download_to_temp", side_effect=fake_download):
                p1 = mgr.fetch("https://contoso.sharepoint.com/file")
                p2 = mgr.fetch("https://contoso.sharepoint.com/file")
            self.assertEqual(p1, p2)
            self.assertEqual(len(calls), 1)  # 2回目はキャッシュ
        finally:
            mgr.cleanup()

    def test_cleanup_removes_temp_dir(self):
        mgr = RemoteFileManager({})
        with tempfile.TemporaryDirectory() as src_dir:
            src = os.path.join(src_dir, "mock.xlsx")
            with open(src, "wb") as f:
                f.write(b"hi")
            with patch.dict(os.environ, {RemoteSource.MOCK_ENV_VAR: src}):
                local = mgr.fetch("https://contoso.sharepoint.com/x")
            temp_dir = os.path.dirname(local)
            self.assertTrue(os.path.isdir(temp_dir))
            mgr.cleanup()
            self.assertFalse(os.path.isdir(temp_dir))

    def test_context_manager_cleans_up(self):
        with tempfile.TemporaryDirectory() as src_dir:
            src = os.path.join(src_dir, "mock.xlsx")
            with open(src, "wb") as f:
                f.write(b"hi")
            with patch.dict(os.environ, {RemoteSource.MOCK_ENV_VAR: src}):
                with RemoteFileManager({}) as mgr:
                    local = mgr.fetch("https://contoso.sharepoint.com/x")
                    temp_dir = os.path.dirname(local)
                    self.assertTrue(os.path.isdir(temp_dir))
            self.assertFalse(os.path.isdir(temp_dir))


if __name__ == "__main__":
    unittest.main()
