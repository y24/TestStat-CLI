import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from utils import RemoteSource
from utils.RemoteSource import (
    DownloadProgress,
    RemoteFileManager,
    RemoteSourceError,
    encode_share_id,
    is_remote_path,
    resolve_az_command,
    resolve_download_url,
)


class FakeResponse:
    def __init__(self, body="{}", headers=None):
        self._body = body.encode("utf-8") if isinstance(body, str) else body
        self._offset = 0
        self.headers = headers or {}

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self._body) - self._offset
        start = self._offset
        end = min(start + size, len(self._body))
        self._offset = end
        return self._body[start:end]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeLogger:
    def __init__(self):
        self.messages = []

    def log(self, message):
        self.messages.append(message)


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


class DownloadProgressTests(unittest.TestCase):
    def test_download_to_temp_writes_progress_with_label_and_count(self):
        stream = io.StringIO()
        progress = DownloadProgress(label="LABEL1", item_index=1, item_total=2, stream=stream)
        body = b"abc" * 100

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "utils.RemoteSource.urllib.request.urlopen",
                return_value=FakeResponse(body, {"Content-Length": str(len(body))}),
            ):
                path = RemoteSource.download_to_temp(
                    "https://dl.example/file",
                    "sample.xlsx",
                    temp_dir,
                    progress=progress,
                )
            with open(path, "rb") as f:
                self.assertEqual(f.read(), body)

        output = stream.getvalue()
        self.assertIn("[1/2]", output)
        self.assertIn("sample.xlsx", output)
        self.assertIn("100.0%", output)
        self.assertNotIn("label=LABEL1", output)


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

    def test_retries_without_select_when_download_url_is_missing(self):
        bodies = [
            json.dumps({"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#shares"}),
            json.dumps({
                "id": "abc",
                "name": "sample.xlsx",
                "@microsoft.graph.downloadUrl": "https://dl.example/abc",
            }),
        ]
        captured_urls = []

        def fake_urlopen(req, timeout=None):
            captured_urls.append(req.full_url)
            return FakeResponse(bodies.pop(0))

        with patch("utils.RemoteSource.urllib.request.urlopen", side_effect=fake_urlopen):
            name, url = resolve_download_url("u!xxx", "tok", timeout=5)

        self.assertEqual(name, "sample.xlsx")
        self.assertEqual(url, "https://dl.example/abc")
        self.assertIn("$select=", captured_urls[0])
        self.assertNotIn("$select=", captured_urls[1])


class GetAccessTokenTests(unittest.TestCase):
    def test_missing_az_raises(self):
        with patch("utils.RemoteSource.resolve_az_command", return_value=None):
            with self.assertRaises(RemoteSourceError) as ctx:
                RemoteSource.get_access_token()
        self.assertIn("Azure CLI", str(ctx.exception))

    def test_not_logged_in_raises(self):
        class Completed:
            returncode = 1
            stdout = ""
            stderr = "Please run 'az login' to setup account."

        with patch("utils.RemoteSource.resolve_az_command", return_value="az.cmd"), \
             patch("utils.RemoteSource.subprocess.run", return_value=Completed()):
            with self.assertRaises(RemoteSourceError) as ctx:
                RemoteSource.get_access_token()
        self.assertIn("az login", str(ctx.exception))

    def test_returns_token(self):
        class Completed:
            returncode = 0
            stdout = "the-token\n"
            stderr = ""

        logger = FakeLogger()
        with patch("utils.RemoteSource.resolve_az_command", return_value="az.cmd"), \
             patch("utils.RemoteSource.subprocess.run", return_value=Completed()) as run:
            self.assertEqual(RemoteSource.get_access_token(logger=logger), "the-token")
        self.assertEqual(run.call_args.args[0][0], "az.cmd")
        self.assertTrue(any("token_length=9" in msg for msg in logger.messages))
        self.assertFalse(any("the-token" in msg for msg in logger.messages))

    def test_az_failure_logs_return_code_and_stderr(self):
        class Completed:
            returncode = 1
            stdout = ""
            stderr = "Please run 'az login' to setup account."

        logger = FakeLogger()
        with patch("utils.RemoteSource.resolve_az_command", return_value="az.cmd"), \
             patch("utils.RemoteSource.subprocess.run", return_value=Completed()):
            with self.assertRaises(RemoteSourceError) as ctx:
                RemoteSource.get_access_token(logger=logger)

        self.assertNotIn("Please run", str(ctx.exception))
        self.assertTrue(any("returncode=1" in msg for msg in logger.messages))
        self.assertTrue(any("az login" in msg for msg in logger.messages))


class ResolveAzCommandTests(unittest.TestCase):
    def test_env_path_takes_precedence(self):
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".test_tmp", "az_path"))
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

        az_path = os.path.join(temp_dir, "az.cmd")
        with open(az_path, "w", encoding="utf-8") as f:
            f.write("@echo off\n")

        with patch.dict(os.environ, {RemoteSource.AZ_CLI_PATH_ENV_VAR: az_path}), \
             patch("utils.RemoteSource.shutil.which", return_value=None):
            logger = FakeLogger()
            self.assertEqual(resolve_az_command(logger=logger), az_path)

        self.assertTrue(any(RemoteSource.AZ_CLI_PATH_ENV_VAR in msg for msg in logger.messages))

    def test_path_lookup_includes_windows_command_names(self):
        calls = []

        def fake_which(name):
            calls.append(name)
            return "C:\\Azure\\az.cmd" if name == "az.cmd" else None

        with patch.dict(os.environ, {RemoteSource.AZ_CLI_PATH_ENV_VAR: ""}, clear=False), \
             patch("utils.RemoteSource.shutil.which", side_effect=fake_which):
            self.assertEqual(resolve_az_command(), "C:\\Azure\\az.cmd")

        self.assertIn("az", calls)
        self.assertIn("az.cmd", calls)

    def test_download_url_log_does_not_include_signed_url(self):
        body = json.dumps({
            "id": "abc",
            "name": "sample.xlsx",
            "@microsoft.graph.downloadUrl": "https://signed.example/secret",
        })
        logger = FakeLogger()

        with patch("utils.RemoteSource.urllib.request.urlopen", return_value=FakeResponse(body)):
            name, url = resolve_download_url("u!xxx", "tok", logger=logger)

        self.assertEqual(name, "sample.xlsx")
        self.assertEqual(url, "https://signed.example/secret")
        self.assertFalse(any("https://signed.example/secret" in msg for msg in logger.messages))
        self.assertTrue(any("download_url=取得済み(非表示)" in msg for msg in logger.messages))

    def test_graph_error_body_is_only_in_debug_log(self):
        err = urllib.error.HTTPError(
            "u",
            500,
            "Internal Server Error",
            {},
            io.BytesIO(b'{"error":"debug detail"}'),
        )
        logger = FakeLogger()

        with patch("utils.RemoteSource.urllib.request.urlopen", side_effect=err):
            with self.assertRaises(RemoteSourceError) as ctx:
                resolve_download_url("u!xxx", "tok", logger=logger)

        self.assertNotIn("debug detail", str(ctx.exception))
        self.assertTrue(any("debug detail" in msg for msg in logger.messages))


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
