"""SharePoint / OneDrive for Business 上の Excel ファイルを取得するモジュール。

リストファイルの ``path`` に SharePoint の共有 URL が指定された場合、
Graph API の ``/shares`` エンドポイント経由でファイルを一時フォルダへ
ダウンロードし、ローカルパスを返す。

設計方針:
- HTTP は標準ライブラリ ``urllib`` のみ（追加依存を持たない）。
- アクセストークンの取得だけ Azure CLI (``az``) に委譲する。
- 一時ファイルは実行単位で管理し、終了時に破棄する。

詳細は docs/sharepoint_remote_list_plan.md を参照。
"""

import base64
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request

# モックモード（CI・オフライン開発用）。
# 環境変数 TESTSTAT_SHAREPOINT_MOCK にローカルの .xlsx パスを指定すると、
# az/Graph を呼ばずにそのファイルを返す。
MOCK_ENV_VAR = "TESTSTAT_SHAREPOINT_MOCK"

GRAPH_RESOURCE = "https://graph.microsoft.com"
DEFAULT_GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
DEFAULT_TIMEOUT_SEC = 60


class RemoteSourceError(Exception):
    """リモートファイル取得時のエラー。"""


def is_remote_path(path):
    """パスが http(s) のリモート URL かどうかを判定する。"""
    if not isinstance(path, str):
        return False
    lowered = path.strip().lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def encode_share_id(url):
    """共有 URL を Graph ``/shares`` の shareId にエンコードする。

    1. URL を UTF-8 で base64 エンコード
    2. 末尾の ``=``（パディング）を削除
    3. ``/`` → ``_``、``+`` → ``-`` に置換
    4. 先頭に ``u!`` を付与
    """
    b64 = base64.b64encode(url.strip().encode("utf-8")).decode("ascii")
    return "u!" + b64.rstrip("=").replace("/", "_").replace("+", "-")


def get_access_token(resource=GRAPH_RESOURCE, logger=None):
    """``az account get-access-token`` でアクセストークンを取得する。"""
    cmd = [
        "az", "account", "get-access-token",
        "--resource", resource,
        "--query", "accessToken",
        "-o", "tsv",
    ]
    try:
        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        raise RemoteSourceError(
            "Azure CLI (az) が見つかりません。インストールのうえ `az login` を実行してください。"
        )
    except OSError as e:
        raise RemoteSourceError(f"Azure CLI の実行に失敗しました: {e}")

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        if "az login" in stderr or "not logged in" in stderr.lower():
            raise RemoteSourceError(
                "Azure にログインしていません。`az login` を実行してください。"
            )
        raise RemoteSourceError(
            f"アクセストークンの取得に失敗しました: {stderr or 'az が異常終了しました'}"
        )

    token = (completed.stdout or "").strip()
    if not token:
        raise RemoteSourceError("アクセストークンが空でした。`az login` の状態を確認してください。")

    if logger:
        logger.log("Graph アクセストークンを取得しました。")
    return token


def resolve_download_url(share_id, token, graph_endpoint=DEFAULT_GRAPH_ENDPOINT,
                         timeout=DEFAULT_TIMEOUT_SEC, logger=None):
    """``/shares/{shareId}/driveItem`` を呼び出し (name, download_url) を返す。"""
    url = (
        f"{graph_endpoint.rstrip('/')}/shares/{share_id}/driveItem"
        "?$select=id,name,@microsoft.graph.downloadUrl"
    )
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise RemoteSourceError(
                "アクセス権がありません (403)。Files.Read.All / Sites.Read.All 相当の"
                "スコープを持つアカウントでのログイン、または管理者同意が必要です。"
            )
        if e.code == 404:
            raise RemoteSourceError(
                "共有 URL を解決できません (404)。発行/埋め込み URL ではなく、"
                "『リンクのコピー』で取得した共有 URL を指定してください。"
            )
        raise RemoteSourceError(f"Graph API エラー: ステータスコード {e.code}")
    except urllib.error.URLError as e:
        raise RemoteSourceError(f"Graph API への接続に失敗しました: {e.reason}")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise RemoteSourceError(f"Graph API の応答を解析できませんでした: {e}")

    name = data.get("name")
    download_url = data.get("@microsoft.graph.downloadUrl")
    if not download_url:
        raise RemoteSourceError(
            "ダウンロード URL を取得できませんでした。対象がファイルでない可能性があります。"
        )

    if logger:
        logger.log(f"ダウンロード URL を解決しました: {name}")
    return name, download_url


def download_to_temp(download_url, file_name, temp_dir,
                     timeout=DEFAULT_TIMEOUT_SEC, logger=None):
    """downloadUrl からファイル本体を取得し temp_dir/<file_name> に保存する。

    downloadUrl は署名付きの一時 URL のため Authorization ヘッダは付与しない。
    """
    safe_name = os.path.basename(file_name or "download.xlsx")
    dest_path = os.path.join(temp_dir, safe_name)

    req = urllib.request.Request(download_url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response, \
                open(dest_path, "wb") as f:
            shutil.copyfileobj(response, f)
    except urllib.error.HTTPError as e:
        raise RemoteSourceError(f"ファイルのダウンロードに失敗しました: ステータスコード {e.code}")
    except urllib.error.URLError as e:
        raise RemoteSourceError(f"ファイルのダウンロードに失敗しました: {e.reason}")
    except OSError as e:
        raise RemoteSourceError(f"一時ファイルの書き込みに失敗しました: {e}")

    if logger:
        logger.log(f"ファイルをダウンロードしました: {dest_path}")
    return dest_path


class RemoteFileManager:
    """リモートファイル取得と一時フォルダのライフサイクルを管理する。

    - 実行単位の一時ディレクトリを生成する。
    - 同一 URL は一度だけダウンロードしてキャッシュする。
    - cleanup() で一時ディレクトリを再帰削除する（context manager 対応）。
    """

    def __init__(self, sharepoint_config=None, logger=None):
        config = sharepoint_config or {}
        self.logger = logger
        self.graph_endpoint = config.get("graph_endpoint", DEFAULT_GRAPH_ENDPOINT)
        self.timeout = config.get("timeout_sec", DEFAULT_TIMEOUT_SEC)
        self.cleanup_enabled = config.get("cleanup", True)
        self._base_temp_dir = config.get("temp_dir") or None

        self._temp_dir = None
        self._token = None
        self._cache = {}  # url -> local path

    def _ensure_temp_dir(self):
        if self._temp_dir is None:
            if self._base_temp_dir:
                os.makedirs(self._base_temp_dir, exist_ok=True)
            self._temp_dir = tempfile.mkdtemp(
                prefix="teststat_", dir=self._base_temp_dir
            )
            if self.logger:
                self.logger.log(f"一時ディレクトリを作成しました: {self._temp_dir}")
        return self._temp_dir

    def fetch(self, url):
        """共有 URL からファイルを取得し、ローカルの一時パスを返す。"""
        if url in self._cache:
            if self.logger:
                self.logger.log(f"キャッシュ済みのファイルを再利用します: {url}")
            return self._cache[url]

        temp_dir = self._ensure_temp_dir()

        # モックモード: az / Graph を呼ばずローカルファイルをコピーして返す。
        mock_path = os.environ.get(MOCK_ENV_VAR)
        if mock_path:
            if not os.path.exists(mock_path):
                raise RemoteSourceError(
                    f"モックファイルが見つかりません ({MOCK_ENV_VAR}): {mock_path}"
                )
            dest_path = os.path.join(temp_dir, os.path.basename(mock_path))
            shutil.copyfile(mock_path, dest_path)
            if self.logger:
                self.logger.log(f"[MOCK] {url} → {dest_path}")
            self._cache[url] = dest_path
            return dest_path

        if self._token is None:
            self._token = get_access_token(logger=self.logger)

        share_id = encode_share_id(url)
        name, download_url = resolve_download_url(
            share_id, self._token,
            graph_endpoint=self.graph_endpoint,
            timeout=self.timeout,
            logger=self.logger,
        )
        local_path = download_to_temp(
            download_url, name, temp_dir,
            timeout=self.timeout, logger=self.logger,
        )
        self._cache[url] = local_path
        return local_path

    def cleanup(self):
        """一時ディレクトリを削除する。"""
        if self._temp_dir and os.path.isdir(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            if self.logger:
                self.logger.log(f"一時ディレクトリを削除しました: {self._temp_dir}")
        self._temp_dir = None
        self._cache = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.cleanup_enabled:
            self.cleanup()
        return False
