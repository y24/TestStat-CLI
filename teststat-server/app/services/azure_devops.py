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


class WorkItemTypeMismatch(AzureDevOpsError):
    """Work Item Type が期待値と一致しない。"""


@dataclass
class WorkItemInfo:
    work_item_id: int
    name: str
    start_date: date | None
    end_date: date | None


@dataclass
class BugWorkItem:
    work_item_id: int
    title: str
    state: str                  # 見送り/完了の判定に使う（Suspend 等）
    created_date: date | None   # 起票日
    finish_date: date | None    # 完了日／見送り確定日（None=未解消）


def fetch_work_item(work_item_id: int, settings: Settings | None = None) -> WorkItemInfo:
    """Work Item を取得し、タイトル・開始日・終了日を返す。"""
    settings = settings or get_settings()
    if settings.azure_devops_use_mock:
        return _mock_work_item(work_item_id)
    return _fetch_work_item_remote(work_item_id, settings)


def fetch_work_item_type(work_item_id: int, settings: Settings | None = None) -> str:
    """Work Item の WorkItemType を返す。"""
    settings = settings or get_settings()
    if settings.azure_devops_use_mock:
        return _mock_work_item_type(work_item_id, settings)
    return _fetch_work_item_type_remote(work_item_id, settings)


def validate_work_item_type(work_item_id: int, settings: Settings | None = None) -> None:
    """testing_id の Work Item Type を確認し、期待値と異なれば WorkItemTypeMismatch を送出する。

    Azure DevOps が未設定（PAT/Organization 未入力かつ mock 無効）の場合はチェックをスキップする。
    AZURE_DEVOPS_TESTING_WIT が空文字の場合もスキップ。
    """
    settings = settings or get_settings()
    if not settings.azure_devops_use_mock and (
        not settings.azure_devops_pat or not settings.azure_devops_organization
    ):
        return
    expected = settings.azure_devops_testing_wit
    if not expected:
        return
    actual = fetch_work_item_type(work_item_id, settings)
    if actual != expected:
        raise WorkItemTypeMismatch(
            f"Work Item {work_item_id} のタイプは '{actual}' です（期待: '{expected}'）"
        )


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


def _mock_work_item_type(work_item_id: int, settings: Settings) -> str:
    if work_item_id <= 0:
        raise WorkItemNotFound(f"Work Item {work_item_id} は存在しません（mock）")
    return settings.azure_devops_testing_wit


# --- 実接続 ---------------------------------------------------------------


def _build_client() -> httpx.Client:
    """HTTP クライアントを生成する。テストでは MockTransport 注入のため差し替える。"""
    return httpx.Client(timeout=_HTTP_TIMEOUT)


def _request(
    path: str,
    params: dict[str, str],
    settings: Settings,
    *,
    method: str = "GET",
    json: object | None = None,
) -> httpx.Response:
    """Azure DevOps REST API を呼ぶ共通ヘルパ（読み取り専用）。

    GET（Work Item 取得）に加え、WIQL の POST も同じ認証・URL 構築・エラー変換で扱える。
    POST 時は `json=` を渡すと httpx が Content-Type: application/json を自動付与する。
    """
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
            response = client.request(method, url, params=params, headers=headers, json=json)
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


def _fetch_work_item_type_remote(work_item_id: int, settings: Settings) -> str:
    params = {
        "api-version": settings.azure_devops_api_version,
        "fields": "System.WorkItemType",
    }
    response = _request(f"workitems/{work_item_id}", params, settings)
    return response.json().get("fields", {}).get("System.WorkItemType") or ""


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


# --- 子チケット（Bug）取得 -------------------------------------------------

# workitems?ids= は 1 リクエストあたり最大 200 件。
_WORKITEMS_BATCH = 200


def fetch_child_bugs(
    work_item_id: int,
    settings: Settings | None = None,
    *,
    bug_work_item_type: str | None = None,
    bug_tag: str | None = None,
) -> list[BugWorkItem]:
    """Work Item の子チケットのうち Bug を取得する。

    IGNORE 対象 State は除外する。Suspend（見送り）対象 State は除外せず、State を保持して返す
    （完了/見送りの振り分けは集計側で行う）。
    """
    settings = settings or get_settings()
    if settings.azure_devops_use_mock:
        return _mock_child_bugs(work_item_id, settings)
    return _fetch_child_bugs_remote(
        work_item_id,
        settings,
        bug_work_item_type=bug_work_item_type,
        bug_tag=bug_tag,
    )


def _configured_bug_fields(settings: Settings) -> list[str]:
    """取得するフィールド参照名（空文字は除外、順序維持で重複排除）。"""
    candidates = [
        settings.azure_devops_title_field,
        settings.azure_devops_bug_state_field,
        *settings.azure_devops_bug_created_date_fields,
        *settings.azure_devops_bug_finish_date_fields,
    ]
    result: list[str] = []
    for name in candidates:
        if name and name not in result:
            result.append(name)
    return result


def _wiql_escape(value: str) -> str:
    return value.replace("'", "''")


def _wiql_child_bug_query(
    work_item_id: int,
    settings: Settings,
    *,
    bug_work_item_type: str | None = None,
    bug_tag: str | None = None,
) -> str:
    bug_wit = _wiql_escape((bug_work_item_type or settings.azure_devops_bug_wit).strip())
    query = (
        "SELECT [System.Id] FROM WorkItems "
        f"WHERE [System.Parent] = {work_item_id} "
        f"AND [System.WorkItemType] = '{bug_wit}'"
    )
    tag = (bug_tag or "").strip()
    if tag:
        query += f" AND [System.Tags] Contains '{_wiql_escape(tag)}'"
    return query


def _fetch_child_bugs_remote(
    work_item_id: int,
    settings: Settings,
    *,
    bug_work_item_type: str | None = None,
    bug_tag: str | None = None,
) -> list[BugWorkItem]:
    params = {"api-version": settings.azure_devops_api_version}

    # ① WIQL で子 Bug の ID 一覧を取得（fields と $expand の併用不可制約を回避）。
    wiql_response = _request(
        "wiql",
        params,
        settings,
        method="POST",
        json={
            "query": _wiql_child_bug_query(
                work_item_id,
                settings,
                bug_work_item_type=bug_work_item_type,
                bug_tag=bug_tag,
            )
        },
    )
    ids = [item["id"] for item in wiql_response.json().get("workItems", []) if "id" in item]
    if not ids:
        return []

    # ② フィールドを 200 件ずつ一括取得。
    field_names = _configured_bug_fields(settings)
    bugs: list[BugWorkItem] = []
    ignore_states = settings.azure_devops_bug_ignore_status_set
    for start in range(0, len(ids), _WORKITEMS_BATCH):
        batch = ids[start : start + _WORKITEMS_BATCH]
        batch_params = {
            "api-version": settings.azure_devops_api_version,
            "ids": ",".join(str(i) for i in batch),
        }
        if field_names:
            batch_params["fields"] = ",".join(field_names)
        response = _request("workitems", batch_params, settings)
        for item in response.json().get("value", []):
            bug = _build_bug(item, settings)
            if bug.state in ignore_states:  # Removed 等は完全除外
                continue
            bugs.append(bug)
    return bugs


def _parse_first_date(fields: dict, field_names: list[str]) -> date | None:
    """候補フィールドを順に見て、最初に解釈できた日付を返す。"""
    for name in field_names:
        parsed = _parse_date(fields.get(name))
        if parsed is not None:
            return parsed
    return None


def _build_bug(item: dict, settings: Settings) -> BugWorkItem:
    fields = item.get("fields", {})
    return BugWorkItem(
        work_item_id=item.get("id", 0),
        title=fields.get(settings.azure_devops_title_field) or "",
        state=fields.get(settings.azure_devops_bug_state_field) or "",
        created_date=_parse_first_date(fields, settings.azure_devops_bug_created_date_fields),
        finish_date=_parse_first_date(fields, settings.azure_devops_bug_finish_date_fields),
    )


def _mock_child_bugs(work_item_id: int, settings: Settings) -> list[BugWorkItem]:
    """動作確認用。実レスポンスの構造を模した決定的なサンプルを返す。

    未解消・完了・対応見送り（Suspend）・除外対象（Removed）を含み、
    IGNORE フィルタはモードに依らず適用する（Suspend は残す）。
    """
    if work_item_id <= 0:
        raise WorkItemNotFound(f"Work Item {work_item_id} は存在しません（mock）")

    samples = [
        (9001, "ログイン不可", "Closed", date(2025, 1, 29), date(2025, 2, 5)),
        (9002, "表示崩れ", "Active", date(2025, 1, 31), None),
        (9006, "計算誤り", "Closed", date(2025, 2, 3), date(2025, 2, 14)),
        (9007, "仕様調整中", "Suspend", date(2025, 2, 6), date(2025, 2, 12)),
        (9003, "帳票印字ずれ", "Closed", date(2025, 2, 10), date(2025, 2, 24)),
        (9004, "タイムアウト", "Active", date(2025, 2, 13), None),
        (9008, "次期対応", "Suspend", date(2025, 2, 18), date(2025, 3, 6)),
        (9009, "軽微な文言", "Suspend", date(2025, 3, 3), None),
        (9005, "重複起票", "Removed", date(2025, 2, 20), None),
    ]
    ignore_states = settings.azure_devops_bug_ignore_status_set
    return [
        BugWorkItem(
            work_item_id=wid,
            title=title,
            state=state,
            created_date=created,
            finish_date=finish,
        )
        for wid, title, state, created, finish in samples
        if state not in ignore_states
    ]

