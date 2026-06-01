"""Azure DevOps 連携サービス。

DevOps 側の情報取得のみ（読み取り専用）。PAT はユーザー環境変数 AZURE_DEVOPS_PAT
から読み取る。AZURE_DEVOPS_USE_MOCK=true の場合は実接続せずモックデータを返す。

HTTP 呼び出しは _request() に集約しており、将来の子チケット（バグ）件数取得など
他エンドポイントからも再利用できるようにしている。
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, datetime

import httpx

from app.config import Settings, get_settings

_HTTP_TIMEOUT = 10.0


class AzureDevOpsError(Exception):
    """Azure DevOps 連携の基底例外（接続失敗・予期しない応答）。"""


class AzureDevOpsNotConfigured(AzureDevOpsError):
    """PAT / Organization など必須設定が無い。"""


class WorkItemNotFound(AzureDevOpsError):
    """指定された Work Item が存在しない（404）。"""


class AzureDevOpsAuthError(AzureDevOpsError):
    """認証・認可エラー（401/403）。"""


@dataclass
class WorkItemInfo:
    work_item_id: int
    name: str
    start_date: date | None
    end_date: date | None


def fetch_work_item(work_item_id: int, settings: Settings | None = None) -> WorkItemInfo:
    """Work Item を取得し、タイトル・開始日・終了日を返す。"""
    settings = settings or get_settings()
    if settings.azure_devops_use_mock:
        return _mock_work_item(work_item_id)
    return _fetch_work_item_remote(work_item_id, settings)


# --- モック ---------------------------------------------------------------


def _mock_work_item(work_item_id: int) -> WorkItemInfo:
    # 動作確認用。0 以下は「存在しない Work Item」として 404 経路をテストできる。
    if work_item_id <= 0:
        raise WorkItemNotFound(f"Work Item {work_item_id} は存在しません（mock）")
    return WorkItemInfo(
        work_item_id=work_item_id,
        name=f"[MOCK] Work Item {work_item_id}",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 6, 30),
    )


# --- 実接続 ---------------------------------------------------------------


def _build_client() -> httpx.Client:
    """HTTP クライアントを生成する。テストでは MockTransport 注入のため差し替える。"""
    return httpx.Client(timeout=_HTTP_TIMEOUT)


def _request(path: str, params: dict[str, str], settings: Settings) -> httpx.Response:
    """Azure DevOps REST API を GET で呼ぶ共通ヘルパ（読み取り専用）。"""
    if not settings.azure_devops_pat or not settings.azure_devops_organization:
        raise AzureDevOpsNotConfigured(
            "AZURE_DEVOPS_PAT と AZURE_DEVOPS_ORGANIZATION を設定してください"
        )

    token = base64.b64encode(f":{settings.azure_devops_pat}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}

    base = f"https://dev.azure.com/{settings.azure_devops_organization}"
    if settings.azure_devops_project:
        base = f"{base}/{settings.azure_devops_project}"
    url = f"{base}/_apis/wit/{path}"

    try:
        with _build_client() as client:
            response = client.get(url, params=params, headers=headers)
    except httpx.HTTPError as exc:  # タイムアウト・接続不可など
        raise AzureDevOpsError(f"Azure DevOps への接続に失敗しました: {exc}") from exc

    if response.status_code == 404:
        raise WorkItemNotFound(f"Work Item が見つかりません: {path}")
    if response.status_code in (401, 403):
        raise AzureDevOpsAuthError("Azure DevOps の認証に失敗しました")
    if response.status_code >= 400:
        raise AzureDevOpsError(
            f"Azure DevOps が予期しない応答を返しました: {response.status_code}"
        )
    return response


def _fetch_work_item_remote(work_item_id: int, settings: Settings) -> WorkItemInfo:
    field_names = _configured_fields(settings)
    params = {"api-version": settings.azure_devops_api_version}
    if field_names:
        # fields はカンマ区切りの参照名リスト。$expand とは併用不可。
        params["fields"] = ",".join(field_names)

    response = _request(f"workitems/{work_item_id}", params, settings)
    fields = response.json().get("fields", {})

    return WorkItemInfo(
        work_item_id=work_item_id,
        name=fields.get(settings.azure_devops_title_field) or "",
        start_date=_parse_date(fields.get(settings.azure_devops_start_date_field)),
        end_date=_parse_date(fields.get(settings.azure_devops_end_date_field)),
    )


def _configured_fields(settings: Settings) -> list[str]:
    """取得するフィールド参照名（空文字は除外、順序維持で重複排除）。"""
    candidates = [
        settings.azure_devops_title_field,
        settings.azure_devops_start_date_field,
        settings.azure_devops_end_date_field,
    ]
    result: list[str] = []
    for name in candidates:
        if name and name not in result:
            result.append(name)
    return result


def _parse_date(value: object) -> date | None:
    """ISO 8601 datetime（'Z'・小数秒付きあり）または日付文字列を date に正規化する。"""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
