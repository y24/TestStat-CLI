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
AZ_CLI_PATH_ENV_VAR = "TESTSTAT_AZ_CLI_PATH"

GRAPH_RESOURCE = "https://graph.microsoft.com"
DEFAULT_GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
DEFAULT_TIMEOUT_SEC = 60


class RemoteSourceError(Exception):
    """リモートファイル取得時のエラー。"""


def _log(logger, message):
    if logger:
        logger.log(message)


def _shorten_message(value, limit=800):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _read_http_error_body(error):
    try:
        return _shorten_message(error.read().decode("utf-8", errors="replace"))
    except Exception:
        return ""


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


def resolve_az_command(logger=None):
    """Azure CLI の実行ファイルを解決する。

    Windows では Python の実行環境によって ``az`` だけでは ``az.cmd`` を
    見つけられない場合があるため、PATH と代表的なインストール先を確認する。
    """
    _log(logger, "Azure CLI の検出を開始します。")

    env_path = os.environ.get(AZ_CLI_PATH_ENV_VAR)
    if env_path:
        expanded = os.path.expandvars(os.path.expanduser(env_path.strip('"')))
        _log(logger, f"{AZ_CLI_PATH_ENV_VAR} が設定されています: {expanded}")
        if os.path.isfile(expanded):
            _log(logger, f"Azure CLI を環境変数から検出しました: {expanded}")
            return expanded
        _log(logger, f"{AZ_CLI_PATH_ENV_VAR} のパスにファイルが見つかりません: {expanded}")

    for name in ("az", "az.cmd", "az.exe"):
        resolved = shutil.which(name)
        _log(logger, f"PATH から Azure CLI を検索しました: {name} -> {resolved or '未検出'}")
        if resolved:
            return resolved

    if os.name == "nt":
        candidates = [
            os.path.join(
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                "Microsoft SDKs", "Azure", "CLI2", "wbin", "az.cmd",
            ),
            os.path.join(
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                "Microsoft SDKs", "Azure", "CLI2", "wbin", "az.cmd",
            ),
            os.path.join(
                os.environ.get("LocalAppData", ""),
                "Programs", "Microsoft SDKs", "Azure", "CLI2", "wbin", "az.cmd",
            ),
        ]
        for candidate in candidates:
            _log(logger, f"Azure CLI の既定インストール先を確認しました: {candidate}")
            if candidate and os.path.isfile(candidate):
                _log(logger, f"Azure CLI を既定インストール先から検出しました: {candidate}")
                return candidate

    _log(logger, "Azure CLI を検出できませんでした。")
    return None


def get_access_token(resource=GRAPH_RESOURCE, logger=None):
    """``az account get-access-token`` でアクセストークンを取得する。"""
    az_command = resolve_az_command(logger=logger)
    if not az_command:
        raise RemoteSourceError(
            "Azure CLI (az) が見つかりません。インストール済みの場合は、"
            f"{AZ_CLI_PATH_ENV_VAR} に az.cmd のフルパスを指定してから `az login` を実行してください。"
        )

    _log(logger, f"Azure CLI で Graph アクセストークンを取得します: command={az_command}, resource={resource}")
    cmd = [
        az_command, "account", "get-access-token",
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
        _log(logger, f"Azure CLI の実行ファイルが起動時に見つかりませんでした: {az_command}")
        raise RemoteSourceError(
            "Azure CLI (az) が見つかりません。インストールのうえ `az login` を実行してください。"
        )
    except OSError as e:
        _log(logger, f"Azure CLI の起動に失敗しました: {e}")
        raise RemoteSourceError(f"Azure CLI の実行に失敗しました: {e}")

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        _log(
            logger,
            "Azure CLI のアクセストークン取得が失敗しました: "
            f"returncode={completed.returncode}, stderr={_shorten_message(stderr) or '(空)'}",
        )
        if "az login" in stderr or "not logged in" in stderr.lower():
            raise RemoteSourceError(
                "Azure にログインしていません。`az login` を実行してください。"
            )
        raise RemoteSourceError(
            "アクセストークンの取得に失敗しました。詳細は `-v` / `--verbose` を付けて確認してください。"
        )

    token = (completed.stdout or "").strip()
    if not token:
        _log(logger, "Azure CLI は正常終了しましたが、アクセストークンが空でした。")
        raise RemoteSourceError("アクセストークンが空でした。`az login` の状態を確認してください。")

    _log(logger, f"Graph アクセストークンを取得しました: token_length={len(token)}")
    return token


def _request_drive_item(url, token, timeout, logger=None):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = _read_http_error_body(e)
        _log(
            logger,
            "Graph API の driveItem 解決に失敗しました: "
            f"status={e.code}, reason={getattr(e, 'reason', '')}, body={body or '(空)'}",
        )
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
        raise RemoteSourceError(
            f"Graph API エラー: ステータスコード {e.code}。詳細は `-v` / `--verbose` を付けて確認してください。"
        )
    except urllib.error.URLError as e:
        _log(logger, f"Graph API への接続に失敗しました: reason={e.reason}")
        raise RemoteSourceError(f"Graph API への接続に失敗しました: {e.reason}")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        _log(logger, f"Graph API の JSON 解析に失敗しました: {e}, body={_shorten_message(body)}")
        raise RemoteSourceError(f"Graph API の応答を解析できませんでした: {e}")

    return data


def resolve_download_url(share_id, token, graph_endpoint=DEFAULT_GRAPH_ENDPOINT,
                         timeout=DEFAULT_TIMEOUT_SEC, logger=None):
    """``/shares/{shareId}/driveItem`` を呼び出し (name, download_url) を返す。"""
    base_url = f"{graph_endpoint.rstrip('/')}/shares/{share_id}/driveItem"

    _log(
        logger,
        "Graph API で共有 URL の driveItem を解決します: "
        f"endpoint={graph_endpoint.rstrip('/')}, share_id_prefix={share_id[:16]}, timeout_sec={timeout}",
    )

    data = _request_drive_item(
        f"{base_url}?$select=id,name,@microsoft.graph.downloadUrl",
        token,
        timeout,
        logger=logger,
    )
    name = data.get("name")
    download_url = data.get("@microsoft.graph.downloadUrl")

    if not download_url:
        _log(
            logger,
            "Graph API 応答に downloadUrl がありません。$select なしで再試行します: "
            f"keys={sorted(data.keys())}",
        )
        data = _request_drive_item(base_url, token, timeout, logger=logger)
        name = data.get("name") or name
        download_url = data.get("@microsoft.graph.downloadUrl")

    if not download_url:
        _log(logger, f"Graph API 応答に downloadUrl がありません: keys={sorted(data.keys())}")
        raise RemoteSourceError(
            "ダウンロード URL を取得できませんでした。対象がファイルでない可能性があります。"
        )

    _log(logger, f"ダウンロード URL を解決しました: name={name}, download_url=取得済み(非表示)")
    return name, download_url


def download_to_temp(download_url, file_name, temp_dir,
                     timeout=DEFAULT_TIMEOUT_SEC, logger=None):
    """downloadUrl からファイル本体を取得し temp_dir/<file_name> に保存する。

    downloadUrl は署名付きの一時 URL のため Authorization ヘッダは付与しない。
    """
    safe_name = os.path.basename(file_name or "download.xlsx")
    dest_path = os.path.join(temp_dir, safe_name)

    req = urllib.request.Request(download_url, method="GET")
    _log(logger, f"署名付き URL からファイルをダウンロードします: file={safe_name}, dest={dest_path}, timeout_sec={timeout}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response, \
                open(dest_path, "wb") as f:
            shutil.copyfileobj(response, f)
    except urllib.error.HTTPError as e:
        body = _read_http_error_body(e)
        _log(
            logger,
            "署名付き URL からのファイルダウンロードに失敗しました: "
            f"status={e.code}, reason={getattr(e, 'reason', '')}, body={body or '(空)'}",
        )
        raise RemoteSourceError(
            f"ファイルのダウンロードに失敗しました: ステータスコード {e.code}。"
            "詳細は `-v` / `--verbose` を付けて確認してください。"
        )
    except urllib.error.URLError as e:
        _log(logger, f"署名付き URL への接続に失敗しました: reason={e.reason}")
        raise RemoteSourceError(f"ファイルのダウンロードに失敗しました: {e.reason}")
    except OSError as e:
        _log(logger, f"一時ファイルの書き込みに失敗しました: dest={dest_path}, error={e}")
        raise RemoteSourceError(f"一時ファイルの書き込みに失敗しました: {e}")

    _log(logger, f"ファイルをダウンロードしました: {dest_path}")
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

        _log(
            self.logger,
            "SharePoint リモートファイル管理を初期化しました: "
            f"graph_endpoint={self.graph_endpoint}, timeout_sec={self.timeout}, "
            f"temp_dir={self._base_temp_dir or '(OS既定)'}, cleanup={self.cleanup_enabled}",
        )

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
        _log(logger=self.logger, message=f"SharePoint ファイル取得を開始します: url={url}")
        if url in self._cache:
            if self.logger:
                self.logger.log(f"キャッシュ済みのファイルを再利用します: {url}")
            return self._cache[url]

        temp_dir = self._ensure_temp_dir()

        # モックモード: az / Graph を呼ばずローカルファイルをコピーして返す。
        mock_path = os.environ.get(MOCK_ENV_VAR)
        if mock_path:
            _log(self.logger, f"SharePoint モックモードを使用します: {MOCK_ENV_VAR}={mock_path}")
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
        else:
            _log(self.logger, "キャッシュ済みの Graph アクセストークンを再利用します。")

        share_id = encode_share_id(url)
        _log(self.logger, f"共有 URL を Graph shareId に変換しました: share_id_prefix={share_id[:16]}")
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
