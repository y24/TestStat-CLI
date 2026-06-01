# Azure DevOps 連携 改修計画

TestStat Studio（`teststat-frontend` + `teststat-server`）に Azure DevOps 連携を導入するための改修計画。

- 作成日: 2026-06-02
- 対象リポジトリ: `teststat-server`（FastAPI）, `teststat-frontend`（Vite + React + TS）

---

## 1. 目的とスコープ

### 背景

TestStat の `testing_id` は **Azure DevOps の Work Item ID** を指している（[既存設計](../teststat-frontend/docs/development_plan.md) で `testing_id` = 外部チケット管理システムのチケットID と定義済み）。これまで手入力していたプロジェクト名・テスト期間を、Work Item から自動取得できるようにする。

### 今回のスコープ

- プロジェクト新規作成画面で、Testing ID を入力し「Azure DevOps から取得」ボタンを押すと、以下を自動入力する。
  - **プロジェクト名** ← Work Item のタイトル（`System.Title`）
  - **開始日 / 終了日** ← `.env` で設定したフィールド名に対応する値
- 取得対象フィールド名は **バックエンドの `.env`** で設定する。
- Azure DevOps への接続有無を切り替えるモックモードを用意する（`AZURE_DEVOPS_USE_MOCK`）。

### 今回のスコープ外（将来拡張として設計に織り込む）

- **バグ件数を子 Work Item の数から定期取得する機能**（[7. 将来拡張](#7-将来拡張バグ件数の定期取得) で設計方針のみ記載）。
- Azure DevOps 側の **更新（書き込み）**。本連携は **読み取り専用**。

### 基本方針

- 連携は **DevOps 側の情報取得のみ**。書き込みは行わない。
- 認証トークン（PAT）は **ユーザー環境変数 `AZURE_DEVOPS_PAT`** から読み取る。`.env` やDB、フロントには保存しない。
- API バージョン・組織名・フィールド名などの設定は **バックエンドの `.env`** に集約する。

### 開発時の制約（重要）

- **開発期間中は実際の Azure DevOps API を実行できない**。動作確認は原則 **モックモード（`AZURE_DEVOPS_USE_MOCK=true`）** で行う。
- このため設計は **モックファースト** とする:
  - モックモードだけで、フロントのボタン押下 → API → フォーム反映の一連が実APIなしで完結すること。
  - **実接続パス（`USE_MOCK=false`）のコードは動作確認では叩けない**ため、公式ドキュメントのサンプル JSON を固定データとした **`httpx.MockTransport` によるユニットテスト**で検証する（[8. テスト方針](#8-テスト方針)）。モード切替後に初めて壊れる事故を防ぐ。
  - モックデータは実レスポンスの構造（`fields` map・日付フォーマット）を忠実に模す。

---

## 2. 全体構成

```
[ブラウザ / teststat-frontend]
   新規プロジェクト作成画面
   Testing ID を入力 →「Azure DevOps から取得」ボタン
        │  GET /api/v1/azure-devops/work-items/{work_item_id}
        ▼
[teststat-server / FastAPI]
   routers/azure_devops.py
        │
   services/azure_devops.py  ── USE_MOCK=true ─▶ モックデータを返す
        │  (USE_MOCK=false)
        │  Basic 認証: base64(":" + AZURE_DEVOPS_PAT)
        ▼
[Azure DevOps REST API]
   GET https://dev.azure.com/{org}/_apis/wit/workitems/{id}
       ?fields=System.Title,<start_field>,<end_field>&api-version=7.1
```

- フロントは PAT を一切扱わない。Azure DevOps へのアクセスは必ずバックエンド経由（PAT 秘匿・CORS 回避・フィールド設定の一元化）。

---

## 3. 設定（バックエンド `.env`）

`teststat-server/.env`（および `.env.example`）に以下を追加する。

```ini
# === Azure DevOps 連携 ===
AZURE_DEVOPS_USE_MOCK=false          # false にすると実際の Azure DevOps に接続
AZURE_DEVOPS_ORGANIZATION=your-org   # Organization 名（URL の dev.azure.com/{ここ}）
# AZURE_DEVOPS_PROJECT=              # Project 名（省略可。WorkItemID は Org 単位で一意）
AZURE_DEVOPS_API_VERSION=7.1

# 取得するフィールド名（Work Item の参照名）
AZURE_DEVOPS_TITLE_FIELD=System.Title
AZURE_DEVOPS_START_DATE_FIELD=Microsoft.VSTS.Scheduling.StartDate
AZURE_DEVOPS_END_DATE_FIELD=Microsoft.VSTS.Scheduling.FinishDate
```

PAT は `.env` ではなく **ユーザー環境変数 `AZURE_DEVOPS_PAT`** で渡す。pydantic-settings は環境変数も読むため、`.env` に書かなくても `AZURE_DEVOPS_PAT` を解決できる。

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `AZURE_DEVOPS_PAT` | 接続時 ○ | （なし） | Personal Access Token。**ユーザー環境変数**で設定。読み取り権限（Work Items: Read）があれば足りる |
| `AZURE_DEVOPS_USE_MOCK` | - | `false` | `true` で実接続せずモックデータを返す（開発・デモ・オフライン用） |
| `AZURE_DEVOPS_ORGANIZATION` | 接続時 ○ | （なし） | 組織名。`https://dev.azure.com/{org}` の `{org}` |
| `AZURE_DEVOPS_PROJECT` | - | （空） | プロジェクト名。Work Item ID は Org 単位で一意なため省略可。指定時は URL に含める |
| `AZURE_DEVOPS_API_VERSION` | - | `7.1` | REST API バージョン |
| `AZURE_DEVOPS_TITLE_FIELD` | - | `System.Title` | プロジェクト名に使う Work Item フィールド参照名 |
| `AZURE_DEVOPS_START_DATE_FIELD` | - | `Microsoft.VSTS.Scheduling.StartDate` | 開始日フィールド参照名。Custom 例: `Custom.ActualStartDate` |
| `AZURE_DEVOPS_END_DATE_FIELD` | - | `Microsoft.VSTS.Scheduling.FinishDate` | 終了日フィールド参照名 |

> **メモ**: 日付フィールドはプロセステンプレートにより異なる（Agile は `Microsoft.VSTS.Scheduling.StartDate` / `FinishDate`、CMMI も同様、カスタムは `Custom.*`）。設定で吸収する。

---

## 4. バックエンド改修（teststat-server）

### 4.1 依存ライブラリ追加

`pyproject.toml` の `dependencies` に HTTP クライアントを追加する。

```toml
"httpx>=0.27.0",
```

`httpx` を採用（同期 `httpx.Client` を使用。タイムアウト・Basic 認証・エラーハンドリングが扱いやすく、将来の非同期化・テスト時のモックも容易）。

### 4.2 `app/config.py` の拡張

`Settings` に Azure DevOps 設定を追加する。

```python
class Settings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")
    allowed_origins: str = Field("*", alias="ALLOWED_ORIGINS")

    # === Azure DevOps ===
    azure_devops_pat: str = Field("", alias="AZURE_DEVOPS_PAT")
    azure_devops_use_mock: bool = Field(False, alias="AZURE_DEVOPS_USE_MOCK")
    azure_devops_organization: str = Field("", alias="AZURE_DEVOPS_ORGANIZATION")
    azure_devops_project: str = Field("", alias="AZURE_DEVOPS_PROJECT")
    azure_devops_api_version: str = Field("7.1", alias="AZURE_DEVOPS_API_VERSION")
    azure_devops_title_field: str = Field("System.Title", alias="AZURE_DEVOPS_TITLE_FIELD")
    azure_devops_start_date_field: str = Field(
        "Microsoft.VSTS.Scheduling.StartDate", alias="AZURE_DEVOPS_START_DATE_FIELD"
    )
    azure_devops_end_date_field: str = Field(
        "Microsoft.VSTS.Scheduling.FinishDate", alias="AZURE_DEVOPS_END_DATE_FIELD"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
```

### 4.3 サービス層 `app/services/azure_devops.py`（新規）

`app/services/` ディレクトリを新設し、Azure DevOps とのやり取りを集約する。ルーター・CRUD からは関数 1 つを呼ぶだけにする。

責務:

- **モード分岐**: `azure_devops_use_mock` が `true` ならモックデータを返す。
- **URL 構築**: `https://dev.azure.com/{org}[/{project}]/_apis/wit/workitems/{id}?fields=...&api-version=...`
- **認証**: `Authorization: Basic base64(":" + PAT)`（ユーザー名空、パスワードに PAT）。
- **フィールド抽出**: 設定されたフィールド参照名で `fields` から値を取り出す。
- **日付正規化**: ADO は `2026-05-01T00:00:00Z` 形式の datetime を返すため、`date`（`YYYY-MM-DD`）へ変換。フィールド未設定・値なしは `None`。
- **エラー変換**: 後述の例外を送出。

想定インターフェース:

```python
@dataclass
class WorkItemInfo:
    work_item_id: int
    name: str                 # System.Title
    start_date: date | None
    end_date: date | None

def fetch_work_item(work_item_id: int) -> WorkItemInfo:
    ...
```

**モックデータ**（`USE_MOCK=true`）: 入力 ID に基づき決定的な値を返す。例: `name=f"[MOCK] Work Item {id}"`, `start_date=2026-05-01`, `end_date=2026-06-30`。存在しない ID を表現するため、特定 ID（例 `0` や `99999999`）では NotFound を返すなどテストしやすくする。

例外設計（`app/services/azure_devops.py` 内に定義）:

| 例外 | 発生条件 | ルーターでの HTTP 変換 |
|------|----------|------------------------|
| `AzureDevOpsNotConfigured` | 非モック時に PAT または Organization 未設定 | `503 Service Unavailable`（設定不備） |
| `WorkItemNotFound` | ADO が 404 を返す | `404 Not Found` |
| `AzureDevOpsAuthError` | ADO が 401/403 を返す | `502 Bad Gateway`（または `500`）＋ログ |
| `AzureDevOpsError` | タイムアウト・5xx・予期しないレスポンス | `502 Bad Gateway` |

### 4.4 スキーマ `app/schemas/azure_devops.py`（新規）

```python
class WorkItemResponse(BaseModel):
    work_item_id: int
    name: str
    start_date: date | None
    end_date: date | None
```

> フロントの `ProjectCreate` と整合させるため、フィールド名は `name` / `start_date` / `end_date` とする（フロントは `planned_start_date` / `planned_end_date` にマッピング）。

### 4.5 ルーター `app/routers/azure_devops.py`（新規）

```python
router = APIRouter(prefix="/api/v1/azure-devops", tags=["azure-devops"])

@router.get("/work-items/{work_item_id}", response_model=WorkItemResponse)
def read_work_item(work_item_id: int) -> WorkItemResponse:
    try:
        info = fetch_work_item(work_item_id)
    except WorkItemNotFound:
        raise HTTPException(status_code=404, detail="Work Item が見つかりません")
    except AzureDevOpsNotConfigured:
        raise HTTPException(status_code=503, detail="Azure DevOps 連携が設定されていません")
    except AzureDevOpsAuthError:
        raise HTTPException(status_code=502, detail="Azure DevOps の認証に失敗しました")
    except AzureDevOpsError:
        raise HTTPException(status_code=502, detail="Azure DevOps への接続に失敗しました")
    return WorkItemResponse(**asdict(info))
```

`app/main.py` に `app.include_router(azure_devops_router)` を追加。`app/routers/__init__.py` に export を追加。

> このエンドポイントは DB を使わない（`get_db` 依存なし）。設定読み込みは `get_settings()` 経由。

### 4.6 ディレクトリ構成（追加分）

```
teststat-server/app/
├── services/
│   ├── __init__.py
│   └── azure_devops.py        # 新規: ADO クライアント + モック + 例外
├── schemas/azure_devops.py    # 新規
└── routers/azure_devops.py    # 新規
```

`pyproject.toml` の `[tool.setuptools].packages` に `app.services` を追加する。

---

## 5. フロントエンド改修（teststat-frontend）

### 5.1 API クライアント / 型

`src/api/types.ts` に追加:

```ts
export interface AzureDevOpsWorkItem {
  work_item_id: number
  name: string
  start_date: string | null
  end_date: string | null
}
```

`src/api/client.ts` に追加:

```ts
export const fetchAzureDevOpsWorkItem = (workItemId: number) =>
  get<AzureDevOpsWorkItem>(`/api/v1/azure-devops/work-items/${workItemId}`)
```

### 5.2 `ProjectEditor.tsx` の改修

新規作成モード（`mode === 'new'`）で、Testing ID 入力欄の近くに「**Azure DevOps から取得**」ボタンを追加する。

挙動:

1. Testing ID が正の整数であることを確認（未入力・不正なら無効化 or エラー表示）。
2. `fetchAzureDevOpsWorkItem(testingId)` を呼ぶ。ボタンはローディング表示（例: 「取得中...」）。
3. 成功時、`name` / `planned_start_date` / `planned_end_date` をフォームに反映する。
   - 日付は `start_date` / `end_date`（`YYYY-MM-DD` 文字列）をそのまま `<input type="date">` に設定。`null` は空文字に。
4. 失敗時、`formError` に分かりやすいメッセージを表示（404: 「Work Item が見つかりません」、503: 「Azure DevOps 連携が未設定です」など `getErrorMessage` で整形）。

既存の自動入力との関係:

- 現状、Testing ID 入力時に **ローカル実績（`fetchProgressSummary`）からプロジェクト名を自動補完**する `useEffect` がある（[ProjectEditor.tsx:74](../teststat-frontend/src/components/ProjectEditor.tsx)）。
- **方針**: ローカル実績からの名前補完は残す（実績が既にあるケースの利便性）。Azure DevOps 取得は **ボタン押下による明示操作**とし、名前＋期間の 3 項目をまとめて上書きする。`autoFilledNameRef` の更新ロジックと衝突しないよう、ボタン経由の反映時も `autoFilledNameRef` を更新する。

UX 補足:

- 取得値はあくまで初期値。ユーザーは反映後に手で編集可能（保存前に確認できる）。
- 編集モード（`mode === 'edit'`）ではボタンを出さない（Testing ID 固定のため）。必要なら将来「再取得」として検討。

### 5.3 画面イメージ（新規作成）

```
Testing ID  [  1001     ] [Azure DevOps から取得]
表示名      [ （自動入力された Work Item タイトル）        ]
テスト期間 開始日 [ 2026-05-01 ]   終了日 [ 2026-06-30 ]
```

---

## 6. セキュリティ・運用

- **PAT の秘匿**: PAT はユーザー環境変数 `AZURE_DEVOPS_PAT` からバックエンドプロセスのみが読む。`.env` への記載・DB 保存・フロント送信・ログ出力は禁止。エラーログに認証ヘッダを残さないこと。
- **読み取り専用**: 実装する HTTP メソッドは `GET` のみ。書き込み API は呼ばない。PAT も Read 権限で足りる。
- **タイムアウト**: `httpx` のタイムアウト（例 10 秒）を設定し、ADO 障害時にバックエンドがハングしないようにする。
- **CORS / 認証**: 既存方針どおり LAN 内・認証なし。ADO アクセスはサーバー集約のため追加の CORS 対応は不要。
- **モックモード**: 開発期間中は実APIを叩けないため `AZURE_DEVOPS_USE_MOCK=true` を**開発時の既定**とする。オフライン開発・デモ・CI でも同様。実接続への切替は本番投入時に `false` にし、その時点で実環境疎通を確認する。

---

## 7. 将来拡張：バグ件数の定期取得

> 今回は実装しないが、サービス層・スキーマを拡張しやすい形にしておく。

### 想定

- ある Work Item（テスト = `testing_id`）の **子チケット（バグ）の件数**を Azure DevOps から定期取得し、品質指標として蓄積・表示する。

### 設計上の考慮点

- **取得方法**: 親 Work Item の子を辿る 2 通り。
  - WIQL（`POST _apis/wit/wiql`）で `[System.Parent] = {id} AND [System.WorkItemType] = 'Bug'` を実行して件数を取得。
  - または `GET _apis/wit/workitems/{id}?$expand=relations` で `System.LinkTypes.Hierarchy-Forward` リンクを数える。
  - 状態別件数（Active/Resolved/Closed など）も取得できるようにフィールド/集計軸を設定可能にしておくと良い。
- **サービス層**: `services/azure_devops.py` に `fetch_child_bug_counts(work_item_id) -> BugCounts` を追加する想定。`fetch_work_item` と認証・URL 構築・例外を共通化できるよう、本改修で **HTTP 呼び出しの共通ヘルパ**（`_request(path, params)`）に切り出しておく。
- **定期実行**: 既存運用（Windows タスクスケジューラ）で、ADO からバグ件数を取得して DB に保存するバッチ／エンドポイントを追加する。新テーブル（例 `bug_snapshots(testing_id, date, total, by_state...)`）を想定。
- **設定追加（将来の `.env`）**: `AZURE_DEVOPS_BUG_WORK_ITEM_TYPE=Bug`、子リンク種別、状態の分類など。
- **フロント**: プロジェクト概要／PB 図にバグ件数推移を重ねる（[既存メモ](../teststat-frontend/docs/development_plan.md) では「バグ実績は初期スコープ外」としており、本拡張で解禁する位置づけ）。

### 今回織り込む準備

- HTTP 呼び出し・認証・例外処理を `fetch_work_item` 専用に書かず、再利用可能な内部ヘルパに分離しておく。
- 設定（`Settings`）は項目追加しやすい構造のまま（pydantic-settings + alias）。

---

## 8. テスト方針

### バックエンド

- **サービス層（モック）**: `AZURE_DEVOPS_USE_MOCK=true` で `fetch_work_item` が期待値を返す／NotFound 用 ID で例外を投げる。
- **サービス層（実接続のスタブ）**: `httpx` のトランスポートをモック（`httpx.MockTransport`）し、
  - 正常レスポンス → フィールド抽出・日付正規化が正しい。
  - 設定したカスタムフィールド名（`Custom.*`）でも値を拾える。
  - 404 → `WorkItemNotFound`、401/403 → `AzureDevOpsAuthError`、タイムアウト/5xx → `AzureDevOpsError`。
  - PAT/Org 未設定（非モック）→ `AzureDevOpsNotConfigured`。
- **ルーター**: 各例外が期待 HTTP ステータスにマッピングされる（FastAPI `TestClient`）。

### フロントエンド

- ボタン押下 → API 呼び出し → フォーム反映の挙動（成功・失敗・ローディング）。
- 取得後にユーザー編集が可能・保存ペイロードが正しい（`planned_start_date`/`planned_end_date` へのマッピング）。

---

## 9. 実装フェーズ・チェックリスト

### Phase A: バックエンド

- [ ] `pyproject.toml` に `httpx` 追加、`app.services` をパッケージに追加
- [ ] `app/config.py` に Azure DevOps 設定を追加
- [ ] `app/services/azure_devops.py`（クライアント・モック・例外・日付正規化・共通 `_request` ヘルパ）
- [ ] `app/schemas/azure_devops.py`（`WorkItemResponse`）
- [ ] `app/routers/azure_devops.py`（`GET /work-items/{id}` + 例外→HTTP 変換）
- [ ] `app/main.py` / `routers/__init__.py` にルーター登録
- [ ] `.env.example` に設定例を追記
- [ ] テスト（モック・MockTransport・ルーター）

### Phase B: フロントエンド

- [ ] `src/api/types.ts` に `AzureDevOpsWorkItem`
- [ ] `src/api/client.ts` に `fetchAzureDevOpsWorkItem`
- [ ] `ProjectEditor.tsx` に「Azure DevOps から取得」ボタン＋反映・エラー・ローディング処理
- [ ] 既存ローカル実績自動補完との整合確認
- [ ] 動作確認（モックモードのバックエンドで疎通）

### Phase C: 将来（本計画ではスコープ外）

- [ ] 子チケット（バグ）件数取得サービス／バッチ／テーブル
- [ ] バグ件数の可視化

---

## 付録: Azure DevOps REST API メモ

- Work Item 取得: `GET https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{id}?api-version=7.1`
  - URI パラメータ: `id`(必須), `organization`(必須), `project`(**省略可** — Work Item ID は Org 単位で一意), `api-version`(必須), `fields`(任意), `$expand`(任意), `asOf`(任意)。
  - 特定フィールドのみ: `&fields=System.Title,Microsoft.VSTS.Scheduling.StartDate,Microsoft.VSTS.Scheduling.FinishDate`（カンマ区切りの参照名リスト）。
  - **`fields` と `$expand` は同時指定できない**（ADO の制約）。今回は `fields` のみなので問題ないが、将来のバグ件数取得（`$expand=relations`）では `fields` と併用せず別リクエスト or WIQL にすること（[7. 将来拡張](#7-将来拡張バグ件数の定期取得) 参照）。
  - `fields` 指定時に**存在しないフィールド参照名**を混ぜるとエラーになり得るため、`.env` で未設定（空文字）のフィールドはクエリから除外する実装にする。
  - 値が無いフィールドはレスポンスの `fields` map から**単に省略される**（エラーにはならない）。サービス層は `fields.get(<参照名>)` で取り出し、未存在は `None` 扱いにする。
- 認証: HTTP Basic。ユーザー名は空、パスワードに PAT。`Authorization: Basic ` + `base64(":" + PAT)`。（このエンドポイントは PAT に `vso.work`（Work Items: Read）相当の権限があれば足りる）
- `$expand` の選択肢: `none`(既定) / `relations` / `fields` / `links` / `all`。子チケットを辿るには `relations`。
- 日付フィールドの値は ISO 8601 datetime（小数秒・`Z` 付きのことがある。例 `2026-05-01T00:00:00.000Z`）。`date`（`YYYY-MM-DD`）に切り出して返す。`datetime.fromisoformat` を使う場合は末尾 `Z` を `+00:00` に置換する等の正規化が必要。
- レスポンス例（抜粋）:

```json
{
  "id": 1001,
  "fields": {
    "System.Title": "サンプルプロジェクト",
    "Microsoft.VSTS.Scheduling.StartDate": "2026-05-01T00:00:00Z",
    "Microsoft.VSTS.Scheduling.FinishDate": "2026-06-30T00:00:00Z"
  }
}
```
