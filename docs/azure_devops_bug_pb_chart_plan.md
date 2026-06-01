# Azure DevOps バグ件数取得 → PB図反映 改修計画

[Azure DevOps 連携 改修計画](./azure_devops_integration_plan.md) の **§7 将来拡張：バグ件数の定期取得** を実装に落とし込む計画。Testing ID（= 親 Work Item）の子チケット（Bug）を取得し、日付ごとの不具合累積・解消をPB図に重ねて表示する。

- 作成日: 2026-06-02
- 対象リポジトリ: `teststat-server`（FastAPI）, `teststat-frontend`（Vite + React + TS）
- 前提: §7 で「HTTP 呼び出し・認証・例外処理を `fetch_work_item` 専用に書かず再利用可能な内部ヘルパに分離しておく」とした方針どおり、`services/azure_devops.py` の `_request()` を再利用する。

---

## 1. 目的とスコープ

### やりたいこと（要件）

1. **Testing ID の Work Item の子チケット（Child）のうち、Work Item Type が Bug のものを抽出**する。
   - Bug の種別名は `.env` の `AZURE_DEVOPS_BUG_WIT=Bug` で指定（プロセステンプレートにより `不具合` 等のことがあるため設定で吸収）。
   - **ステータスが `Removed`（`AZURE_DEVOPS_BUG_IGNORE_STATUS=Removed`）のものを除外**。カンマ区切りで複数指定可。
   - **ステータスが `Suspend`（`AZURE_DEVOPS_BUG_SUSPEND_STATUS=Suspend`）のものは除外せず「対応見送り」として扱う**（完了日＝見送り確定日で別カテゴリ集計）。カンマ区切りで複数指定可。
2. 取得した情報を **DB に記録**する。取得のたびに **Testing ID ごとに洗替**（既存 `replace_progress` と同じ delete → insert 方式）。
3. **PB図に、その Testing ID の不具合を日付ごとに累積（積み上げエリア）で表示**。上から **不具合検出数（未解消・薄い赤）／対応見送り数（薄い黄）／完了数（薄い緑）** の順に積む。積み上げ上端＝検出累積。
4. チケットの **作成日**（`AZURE_DEVOPS_BUG_CREATED_DATE_FIELD=<フィールド名>`）を、その不具合の **起票日** とする。
5. チケットの **完了日**（`AZURE_DEVOPS_BUG_FINISH_DATE_FIELD=<フィールド名>`）を、その不具合の **完了日／見送り確定日** とする。
   - State が Suspend 以外なら → 完了日以降は **完了（緑）**。
   - State が Suspend なら → 完了日以降は **対応見送り（黄）**。
   - 完了日が未設定（空）の不具合は、State に関わらず **未解消（赤）** とみなす。

### スコープ外

- Azure DevOps 側の更新（書き込み）。本連携は引き続き **読み取り専用**（DBへの書き込みは自社DBのみ）。
- バグの状態遷移履歴の保持（今回は「現時点の各バグの起票日・完了日」のみ。日次スナップショットの履歴テーブルは作らない）。
  - 起票日・完了日を持てば任意の日付断面の累積・解消が **計算で再現できる** ため、日次スナップショット不要。

### 基本方針（既存連携を踏襲）

- ADO アクセスは必ずバックエンド経由。PAT は **ユーザー環境変数 `AZURE_DEVOPS_PAT`**。フロント・DB・ログに残さない。
- 設定（種別名・除外ステータス・フィールド参照名）は **バックエンドの `.env`** に集約。
- **モックファースト**: 開発中は実 API を叩けないため `AZURE_DEVOPS_USE_MOCK=true` を既定とし、モックモードだけで「取得→DB洗替→PB図反映」が完結すること。実接続パスは `httpx.MockTransport` のユニットテストで検証する。

---

## 2. 全体構成

```
[ブラウザ / teststat-frontend]
   PB図パネル：「不具合を取得」ボタン押下
        │  POST /api/v1/projects/{testing_id}/bugs/sync
        ▼
[teststat-server / FastAPI]
   routers/bug.py  ─▶ services/azure_devops.fetch_child_bugs(testing_id)
        │                     │  (USE_MOCK=false)
        │                     │  ① WIQL で子 Bug の ID 一覧を取得（POST _apis/wit/wiql）
        │                     │  ② workitems?ids=... でフィールド一括取得（GET、200件ごと）
        │                     ▼
        │            [Azure DevOps REST API]（読み取り専用）
        │
        ▼  crud/bug.replace_bugs(testing_id, bugs)  ← Testing ID 単位で洗替
   [DB] bug_snapshots テーブル

[PB図表示時]
   GET /api/v1/projects/{testing_id}/pb-chart
        │  crud/pb_chart.get_pb_chart() が bug_snapshots を読み、
        │  日付ごとの「検出累積／解消累積／未解消」を series に同梱
        ▼
   フロントは右Y軸に積み上げエリア（赤=未解消, 緑=解消済）を重畳描画
```

- バグ取得は **明示操作（ボタン）** をトリガとする。将来は Windows タスクスケジューラ／CLI から同エンドポイントを叩いて定期取得も可能（[§9](#9-運用定期取得への拡張)）。
- PB図取得（GET pb-chart）は **DB だけを読む**。ADO へは行かない（描画のたびに ADO を叩かない）。

---

## 3. 設定（バックエンド `.env`）

`teststat-server/.env` / `.env.example` に追記する。

```ini
# === Azure DevOps バグ取得 ===
AZURE_DEVOPS_BUG_WIT=Bug                                   # 子チケットのうち抽出する Work Item Type
AZURE_DEVOPS_BUG_IGNORE_STATUS=Removed                     # 完全除外する State（カンマ区切り・複数可）
AZURE_DEVOPS_BUG_SUSPEND_STATUS=Suspend                    # 「対応見送り」として扱う State（カンマ区切り・複数可）
AZURE_DEVOPS_BUG_CREATED_DATE_FIELD=System.CreatedDate     # 起票日に使うフィールド参照名
AZURE_DEVOPS_BUG_FINISH_DATE_FIELD=Microsoft.VSTS.Common.ClosedDate  # 完了日／見送り確定日に使うフィールド参照名
AZURE_DEVOPS_BUG_STATE_FIELD=System.State                  # 除外/見送り判定に使う State フィールド参照名
```

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `AZURE_DEVOPS_BUG_WIT` | - | `Bug` | 抽出対象の Work Item Type 名。`不具合` 等のローカライズ／カスタム種別に対応 |
| `AZURE_DEVOPS_BUG_IGNORE_STATUS` | - | （空） | **完全除外**する State 名。カンマ区切りで複数。前後空白は無視。空なら除外なし |
| `AZURE_DEVOPS_BUG_SUSPEND_STATUS` | - | （空） | **「対応見送り」**として扱う State 名（除外せず黄カテゴリに集計）。カンマ区切りで複数。前後空白は無視 |
| `AZURE_DEVOPS_BUG_CREATED_DATE_FIELD` | - | `System.CreatedDate` | 起票日フィールド参照名 |
| `AZURE_DEVOPS_BUG_FINISH_DATE_FIELD` | - | `Microsoft.VSTS.Common.ClosedDate` | 完了日／見送り確定日フィールド参照名。値なし＝未解消（赤） |
| `AZURE_DEVOPS_BUG_STATE_FIELD` | - | `System.State` | 除外/見送り判定に読む State フィールド参照名 |

> 既存の `AZURE_DEVOPS_ORGANIZATION` / `AZURE_DEVOPS_PROJECT` / `AZURE_DEVOPS_API_VERSION` / `AZURE_DEVOPS_PAT` / `AZURE_DEVOPS_USE_MOCK` をそのまま利用する。
> `IGNORE` と `SUSPEND` の両方に同じ State を書いた場合は **除外（IGNORE）を優先**する。

`app/config.py` の `Settings` に上記6項目を追加し、除外／見送りステータスを集合化するプロパティを設ける。

```python
azure_devops_bug_wit: str = Field("Bug", alias="AZURE_DEVOPS_BUG_WIT")
azure_devops_bug_ignore_status: str = Field("", alias="AZURE_DEVOPS_BUG_IGNORE_STATUS")
azure_devops_bug_suspend_status: str = Field("", alias="AZURE_DEVOPS_BUG_SUSPEND_STATUS")
azure_devops_bug_created_date_field: str = Field("System.CreatedDate", alias="AZURE_DEVOPS_BUG_CREATED_DATE_FIELD")
azure_devops_bug_finish_date_field: str = Field("Microsoft.VSTS.Common.ClosedDate", alias="AZURE_DEVOPS_BUG_FINISH_DATE_FIELD")
azure_devops_bug_state_field: str = Field("System.State", alias="AZURE_DEVOPS_BUG_STATE_FIELD")

@staticmethod
def _csv_set(value: str) -> set[str]:
    return {s.strip() for s in value.split(",") if s.strip()}

@property
def azure_devops_bug_ignore_status_set(self) -> set[str]:
    return self._csv_set(self.azure_devops_bug_ignore_status)

@property
def azure_devops_bug_suspend_status_set(self) -> set[str]:
    # IGNORE と重複した State は除外を優先（見送り集合からは外す）
    return self._csv_set(self.azure_devops_bug_suspend_status) - self.azure_devops_bug_ignore_status_set
```

---

## 4. バックエンド改修（teststat-server）

### 4.1 サービス層 `app/services/azure_devops.py`（拡張）

#### 4.1.1 共通ヘルパに POST を追加

現状 `_request()` は GET 専用。WIQL は POST のため、メソッドを引数化する（既存呼び出しは GET のままで互換）。

```python
def _request(path, params, settings, *, method="GET", json=None) -> httpx.Response:
    ...
    response = client.request(method, url, params=params, headers=headers, json=json)
    ...
```

> 認証・URL 構築・404/401/403/5xx → 例外変換はそのまま再利用。WIQL は `Content-Type: application/json` が要るが `httpx` の `json=` 指定で自動付与される。

#### 4.1.2 取得関数

```python
@dataclass
class BugWorkItem:
    work_item_id: int
    title: str
    state: str                  # 見送り/完了の判定に使う（Suspend 等）
    created_date: date | None   # 起票日
    finish_date: date | None    # 完了日／見送り確定日（None=未解消）

def fetch_child_bugs(work_item_id: int, settings: Settings | None = None) -> list[BugWorkItem]:
    settings = settings or get_settings()
    if settings.azure_devops_use_mock:
        return _mock_child_bugs(work_item_id, settings)
    return _fetch_child_bugs_remote(work_item_id, settings)
```

**実接続（2 段階）**:

1. **WIQL で子 Bug の ID 一覧**を取得（`fields` と `$expand` の併用不可制約を回避するため、まず ID だけ取る）。

   `POST https://dev.azure.com/{org}[/{project}]/_apis/wit/wiql?api-version=7.1`
   ```json
   {"query": "SELECT [System.Id] FROM WorkItems WHERE [System.Parent] = <id> AND [System.WorkItemType] = '<BUG_WIT>'"}
   ```
   - `[System.Parent] = <id>` で **直下の子（Child）** に限定。レスポンス `workItems[].id` を集める。
   - 除外ステータスは **取得後に Python 側で除外**する（WIQL に `AND [System.State] NOT IN (...)` を足してもよいが、テスト容易性と「設定の空/複数」を素直に扱うため Python フィルタを正とする）。

2. **フィールド一括取得**: 集めた ID を 200 件ずつ分割し
   `GET _apis/wit/workitems?ids=1,2,3&fields=System.Title,<state>,<created>,<finish>&api-version=7.1`
   - 各 `value[].fields` から State・起票日・完了日・タイトルを取り出す。
   - 日付は既存 `_parse_date()`（ISO8601 / `Z` / 小数秒対応）で `date` に正規化。完了日が無いものは `finish_date=None`。
   - `state in settings.azure_devops_bug_ignore_status_set` のものを **除外**（Removed 等）。**Suspend は除外しない**（State をそのまま保持し、見送り判定は集計時に行う）。

**取得フィールド**は `_configured_bug_fields(settings)` で `[title, state, created, finish]` を空文字除外・重複排除して組み立てる（既存 `_configured_fields` と同パターン）。

**モック** `_mock_child_bugs(work_item_id, settings)`:
- `work_item_id <= 0` は `WorkItemNotFound`（親不在の経路をテスト）。
- 決定的なサンプル（例）を返す。実レスポンス構造を模し、**未解消（finish_date=None）・完了・対応見送り（Suspend）・除外対象（Removed）** を必ず1件以上含める:
  | bug id | created | finish | state | カテゴリ |
  |--------|---------|--------|-------|----------|
  | 9001 | 2026-05-02 | 2026-05-06 | Closed | 完了（緑） |
  | 9002 | 2026-05-03 | None | Active | 未解消（赤） |
  | 9003 | 2026-05-08 | 2026-05-15 | Closed | 完了（緑） |
  | 9004 | 2026-05-10 | None | Active | 未解消（赤） |
  | 9007 | 2026-05-09 | 2026-05-13 | **Suspend** | 対応見送り（黄） |
  | 9005 | 2026-05-11 | None | **Removed** | 除外（結果に出ない） |
- 除外（IGNORE）フィルタはモックでも適用。Suspend はそのまま返し、集計で黄カテゴリになることを確認できるようにする。

**例外**: 既存の `AzureDevOpsNotConfigured` / `WorkItemNotFound` / `AzureDevOpsAuthError` / `AzureDevOpsError` を流用（新規例外は追加しない）。

### 4.2 モデル `app/models/bug.py`（新規）

「現時点の各バグ」を保持する。Testing ID 単位で洗替する。

```python
class BugSnapshot(Base):
    __tablename__ = "bug_snapshots"
    id: Mapped[int]               # PK
    testing_id: Mapped[int]       # FK projects.testing_id (ondelete CASCADE), index
    bug_work_item_id: Mapped[int] # ADO 上のバグ Work Item ID
    title: Mapped[str | None]
    state: Mapped[str | None]
    created_date: Mapped[date | None]  # 起票日
    finish_date: Mapped[date | None]   # 完了日（NULL=未解消）
    fetched_at: Mapped[datetime]       # 取得時刻（スナップショット時刻）
```

- `app/models/__init__.py` に `BugSnapshot` を追加。
- **FK は `projects.testing_id`**（プロジェクトが存在することを前提に取得するため。プロジェクト削除で連動削除）。

### 4.3 Alembic マイグレーション（新規）

`alembic/versions/20260602_0011_add_bug_snapshots.py`（`down_revision = "20260602_0010"`）。
`bug_snapshots` を作成し、`testing_id` に index、`projects.testing_id` への FK（`ondelete="CASCADE"`）を張る。

### 4.4 スキーマ `app/schemas/bug.py`（新規）

```python
class BugSyncResponse(BaseModel):
    testing_id: int
    fetched: int                  # 洗替後の総件数（IGNORE 除外後・Suspend 含む）
    open_count: int               # うち未解消（赤）
    suspended_count: int          # うち対応見送り（黄）
    resolved_count: int           # うち完了（緑）
    fetched_at: datetime
```

### 4.5 CRUD `app/crud/bug.py`（新規）

```python
def replace_bugs(db, testing_id, bugs: list[BugWorkItem], fetched_at) -> BugSyncResponse:
    # 既存 replace_progress と同じ「洗替」: delete → insert
    db.execute(delete(BugSnapshot).where(BugSnapshot.testing_id == testing_id))
    db.add_all([BugSnapshot(...) for b in bugs])
    ...

def get_bug_cumulative(db, testing_id, date_range, suspend_states: set[str]) -> dict[date, tuple[int, int, int]]:
    """日付ごとの (未解消 open, 対応見送り suspended, 完了 resolved) を返す。
       検出累積(d)  = created_date <= d の件数
       見送り累積(d) = state ∈ suspend_states かつ finish_date≠NULL かつ finish_date <= d
       完了累積(d)   = state ∉ suspend_states かつ finish_date≠NULL かつ finish_date <= d
       未解消(d)     = 検出累積(d) - 見送り累積(d) - 完了累積(d)
    """
```

- `get_bug_cumulative` は全 `BugSnapshot` 行を1回読み、`created_date` / `finish_date` / `state` を Python 側で日付レンジに対して累積カウントする（行数は高々数百件で十分軽い）。`suspend_states` は `settings.azure_devops_bug_suspend_status_set` を渡す。
- 完了日が未設定の Bug は state に関わらず未解消（open）に残る（Suspend でも finish_date が無ければ赤）。

### 4.6 PB図への統合 `app/crud/pb_chart.py` / `app/schemas/pb_chart.py`

**スキーマ拡張** — `PbChartSeriesItem` に2フィールド追加（不具合データが無い Testing ID では `None`）:

```python
class PbChartSeriesItem(BaseModel):
    date: date
    planned_remaining: int | None
    actual_remaining: int | None
    planned_completed_daily: int | None
    actual_completed_daily: int | None
    bug_open: int | None          # 未解消（赤エリアの高さ）
    bug_suspended: int | None     # 対応見送り累積（黄エリアの高さ）
    bug_resolved: int | None      # 完了累積（緑エリアの高さ）
```

`PbChartResponse` に追加:
```python
    has_bugs: bool               # 1件でも bug_snapshots があるか
    bugs_updated_at: datetime | None  # max(fetched_at)
```

> 互換性: 既存フィールドは温存。`bug_open` / `bug_suspended` / `bug_resolved` を増やすだけなので既存フロントは無視できる（破壊的変更なし）。積み上げ順は下から resolved → suspended → open。

**range（日付軸）の扱い** — バグの起票日・完了日が計画／実績レンジ外に出ることがある。バグエリアが途中で切れないよう、**bug の `created_date` の最小・`finish_date` の最大も range に含める**。

```python
# 既存 range_from/range_to 計算の後に:
bug_dates = [全 created_date] + [全 finish_date(非NULL)]
if bug_dates:
    range_from = min(range_from or min(bug_dates), min(bug_dates))
    range_to   = max(range_to   or max(bug_dates), max(bug_dates))
```
- 計画も実績もバグも無い場合は従来どおり「データなし」レスポンス。
- バグのみ存在（計画・実績なし）でも range が決まり、バグエリアだけのPB図を描ける。

**series 生成** — `date_list` 確定後に `get_bug_cumulative()` を呼び、各日の `bug_open` / `bug_suspended` / `bug_resolved` を `_build_series` の各 item に載せる（`_build_series` に `bug_cumulative: dict[date, tuple[int,int,int]]` を渡す）。`has_bugs=False` のときは全日 `None`。

### 4.7 ルーター `app/routers/bug.py`（新規）

```python
router = APIRouter(prefix="/api/v1", tags=["bugs"])

@router.post("/projects/{testing_id}/bugs/sync", response_model=BugSyncResponse)
def sync_bugs(testing_id: int, db: Session = Depends(get_db)) -> BugSyncResponse:
    # プロジェクト存在確認（get_project が 404）
    get_project(db, testing_id)
    try:
        bugs = fetch_child_bugs(testing_id)
    except WorkItemNotFound:
        raise HTTPException(404, "親 Work Item が見つかりません")
    except AzureDevOpsNotConfigured:
        raise HTTPException(503, "Azure DevOps 連携が設定されていません")
    except AzureDevOpsAuthError:
        raise HTTPException(502, "Azure DevOps の認証に失敗しました")
    except AzureDevOpsError:
        raise HTTPException(502, "Azure DevOps への接続に失敗しました")
    try:
        return replace_bugs(db, testing_id, bugs, datetime.now(UTC).replace(tzinfo=None))
    except Exception:
        db.rollback()
        raise
```

- `app/routers/__init__.py` に `bug_router` を追加、`app/main.py` で `include_router(bug_router)`。
- 例外→HTTP の対応は既存 `azure_devops.py` ルーターと統一。

### 4.8 追加ファイル一覧

```
teststat-server/app/
├── models/bug.py            # 新規: BugSnapshot
├── schemas/bug.py           # 新規: BugSyncResponse
├── crud/bug.py              # 新規: replace_bugs / get_bug_cumulative
├── routers/bug.py           # 新規: POST .../bugs/sync
├── services/azure_devops.py # 拡張: _request に method/json, fetch_child_bugs, _mock_child_bugs
├── config.py                # 拡張: バグ取得5設定 + ignore_status_set
├── crud/pb_chart.py         # 拡張: bug 累積を series/range に統合
└── schemas/pb_chart.py      # 拡張: bug_open/bug_resolved, has_bugs/bugs_updated_at
alembic/versions/20260602_0011_add_bug_snapshots.py  # 新規
```

---

## 5. フロントエンド改修（teststat-frontend）

### 5.1 型 / API クライアント

`src/api/types.ts`:
```ts
export interface PbChartSeries {
  // 既存 ... に追加
  bug_open: number | null
  bug_suspended: number | null
  bug_resolved: number | null
}
export interface PbChartResponse {
  // 既存 ... に追加
  has_bugs: boolean
  bugs_updated_at: string | null
}
export interface BugSyncResult {
  testing_id: number
  fetched: number
  open_count: number
  suspended_count: number
  resolved_count: number
  fetched_at: string
}
```

`src/api/client.ts`:
```ts
export const syncAzureDevOpsBugs = (testing_id: number) =>
  request<BugSyncResult>(`/api/v1/projects/${testing_id}/bugs/sync`, { method: 'POST' })
```

### 5.2 レイヤートグル

`src/types/ui.ts` の `ChartLayers` に `bugs: boolean` を追加。`PbChartPanel.tsx` の初期値・チェックボックス（「不具合」）を追加。

### 5.3 描画（`src/charts/pbChartOptions.ts`）

- **右 Y 軸（yAxisIndex=1）** を追加: `name: '件数（不具合）'`、`splitLine.show: false`。左軸（テスト件数）とスケールを分離。
  - **右軸の上限は段階的**にする（少件数で全体を占有しないように）。検出累積のピーク `peak = max(bug_open + bug_suspended + bug_resolved)` を覆う最小ステップ値を `max` に設定: `30 → 50 → 70 → 90 …`（`peak<=30`→30、超えたら +20 刻み）。
    ```ts
    const steppedBugMax = (peak: number) => (peak <= 30 ? 30 : Math.ceil((peak - 30) / 20) * 20 + 30)
    ```
  - **両軸とも `min: 0`** を明示し、0 ライン（バーンダウンの 0 と不具合の 0）を揃える。左軸を自動 min のままにすると負の日別補正値に引っ張られて軸が負側へ伸びるため、左軸も `min: 0` を設定する。
- `layers.bugs` のとき **積み上げエリア3系列**を追加（`stack: 'bug'`, `yAxisIndex: 1`, `areaStyle`, `symbol: 'none'`）。積み上げは下から緑→黄→赤の順:
  - 「完了不具合(累積)」: data = `bug_resolved`、緑 `rgba(46,160,67,0.18)`（線 `rgba(46,160,67,0.6)`）— **下段**
  - 「対応見送り(累積)」: data = `bug_suspended`、黄 `rgba(214,170,0,0.18)`（線 `rgba(214,170,0,0.7)`）— **中段**
  - 「未解消不具合」: data = `bug_open`、赤 `rgba(214,69,111,0.16)`（線 `rgba(214,69,111,0.65)`）— **上段**
  - 積み上げ上端 = 検出累積。緑・黄が増え赤が縮む挙動になる。
  - z は実績線（z:6）より下（例 z:0〜2）に置き、バーンダウン線を隠さない。
- `buildChartNotices` に「不具合未取得」（`has_bugs===false`）を追加してもよい（任意）。
- `bug_*` が全 `null`（不具合なし）または `layers.bugs` オフのときは右軸・エリアを描かない。

### 5.4 取得ボタン（`PbChartPanel.tsx`）

- ツールバーに「**不具合を取得**」ボタン。押下で `syncAzureDevOpsBugs(testing_id)` → 完了後に PB図を再取得（`fetchPbChart`）。
- ローディング表示（「取得中...」）、結果トースト/メタ（例: 「不具合 6 件（未解消 2 / 見送り 1 / 完了 3）」）、`bugs_updated_at` を「不具合最終取得」として表示。
- 失敗時は `getErrorMessage` でメッセージ表示（503: 未設定 / 404: 親不在 / 502: 接続失敗）。
- 編集モード等は不要。PB図パネル内に閉じる。

---

## 6. PB図の意味づけ（計算仕様）

ある日付 d について（バグ集合 B＝IGNORE 除外後、各バグは起票日 c・完了日 f・State s、見送り State 集合 S）:

- 検出累積  `detected(d) = |{ b∈B : c_b ≤ d }|`
- 見送り累積 `suspended(d) = |{ b∈B : s_b∈S かつ f_b≠NULL かつ f_b ≤ d }|`
- 完了累積  `resolved(d) = |{ b∈B : s_b∉S かつ f_b≠NULL かつ f_b ≤ d }|`
- 未解消   `open(d) = detected(d) − suspended(d) − resolved(d)`

PB図（右軸・積み上げエリア、下→上）:
- 緑エリア高 = `resolved(d)`（下段・完了）
- 黄エリア高 = `suspended(d)`（中段・対応見送り）
- 赤エリア高 = `open(d)`（上段・未解消）
- エリア上端 = `detected(d)`（検出累積、単調増加）

→ 「上から 不具合検出数(赤)／対応見送り(黄)／完了(緑)」を満たす。完了日が範囲より後／未設定のバグは、その日時点では赤（未解消）に積まれる。Suspend のバグは完了日（見送り確定日）以降に黄へ移る。

イメージは [pb_chart_with_bugs_mockup.html](./pb_chart_with_bugs_mockup.html) を参照。

---

## 7. テスト方針

### バックエンド
- **サービス（モック）**: `fetch_child_bugs` が件数・起票日・完了日・State を返す／`Removed` が除外される／`Suspend` は除外されず残る／`work_item_id<=0` で `WorkItemNotFound`。
- **サービス（MockTransport）**: WIQL POST → ID 一覧、`workitems?ids=` GET → フィールド抽出・日付正規化、200件超で複数バッチに分割、`ignore_status` 除外（`suspend_status` は残す）、401/404/5xx → 各例外。
- **CRUD**: `replace_bugs` が洗替（2回呼んで重複しない）。`get_bug_cumulative` が `open/suspended/resolved` を境界日（起票日当日・完了日当日）含めて正しく数える／Suspend が黄、その他完了が緑、完了日なしは赤に分かれる。
- **pb_chart**: バグ込みで `bug_open/bug_suspended/bug_resolved` が series に載る・range がバグ日付で拡張される・バグのみでも描画レスポンスになる・バグなしは全 `None`＋`has_bugs=False`。
- **ルーター**: `bugs/sync` の例外→HTTP（404/503/502）と成功レスポンス。

### フロントエンド
- 「不具合を取得」押下 → sync → 再取得 → 右軸エリア描画。レイヤートグルで表示/非表示。`has_bugs=false` 時にエリアが出ない。

---

## 8. セキュリティ・運用上の注意

- 読み取り専用（ADO へは GET/WIQL の参照のみ）。PAT は環境変数のみ、ログ・レスポンスに出さない。
- `workitems?ids=` は **最大 200 件/リクエスト**。子バグが多い場合に分割必須。
- WIQL 結果が 0 件なら ID 取得 API を呼ばず空リストを返す（無駄な GET を避ける）。
- `fields` に存在しないフィールド参照名を混ぜるとエラーになり得るため、空設定のフィールドはクエリから除外（既存 `_configured_fields` と同方針）。

---

## 9. 運用：定期取得への拡張

- 本計画で作る `POST /projects/{id}/bugs/sync` は **冪等（洗替）** なので、Windows タスクスケジューラや CLI から定期的に叩けば自動更新になる。
- 将来、全プロジェクト一括同期 `POST /bugs/sync-all` を足す余地あり（今回はスコープ外）。

---

## 10. 実装フェーズ・チェックリスト

### Phase 1: バックエンド取得・保存
- [ ] `config.py` にバグ取得6設定 + `ignore_status_set` / `suspend_status_set`
- [ ] `.env.example` 追記
- [ ] `services/azure_devops.py`: `_request` を method/json 対応化 + `fetch_child_bugs` + `_mock_child_bugs` + `_configured_bug_fields`
- [ ] `models/bug.py`（`BugSnapshot`）+ `models/__init__.py`
- [ ] Alembic `20260602_0011_add_bug_snapshots`
- [ ] `schemas/bug.py`, `crud/bug.py`（`replace_bugs` / `get_bug_cumulative`）
- [ ] `routers/bug.py` + `routers/__init__.py` + `main.py` 登録
- [ ] テスト（モック / MockTransport / CRUD / ルーター）

### Phase 2: PB図統合
- [ ] `schemas/pb_chart.py` に `bug_open/bug_suspended/bug_resolved`, `has_bugs/bugs_updated_at`
- [ ] `crud/pb_chart.py` で range 拡張 + series へ累積同梱
- [ ] テスト（pb_chart のバグ統合）

### Phase 3: フロント
- [ ] `types.ts` / `client.ts`（`syncAzureDevOpsBugs`, 型拡張）
- [ ] `ui.ts` `ChartLayers.bugs` + `PbChartPanel` トグル・取得ボタン・メタ表示
- [ ] `pbChartOptions.ts` 右軸 + 積み上げエリア（赤=未解消 / 黄=対応見送り / 緑=完了）
- [ ] 動作確認（モックモードのバックエンドで疎通）

---

## 付録: Azure DevOps REST API メモ（バグ取得）

- **WIQL**: `POST https://dev.azure.com/{org}[/{project}]/_apis/wit/wiql?api-version=7.1`
  - body: `{"query": "SELECT [System.Id] FROM WorkItems WHERE [System.Parent] = <id> AND [System.WorkItemType] = 'Bug'"}`
  - レスポンス: `{"workItems": [{"id": 9001}, {"id": 9003}, ...]}`（ID のみ。フィールド値は含まれない）
- **フィールド一括取得**: `GET _apis/wit/workitems?ids=9001,9003&fields=System.Title,System.State,System.CreatedDate,Microsoft.VSTS.Common.ClosedDate&api-version=7.1`
  - レスポンス: `{"count": n, "value": [{"id": 9001, "fields": {...}}, ...]}`
  - `ids` は最大 200。`fields` と `$expand` は併用不可（ID 取得とフィールド取得を分けているため問題なし）。
  - 値が無いフィールドは `fields` から省略される（→ `None` 扱い）。
- **日付フィールド**: ISO 8601 datetime（`Z`・小数秒あり）。`_parse_date()` で `date` へ正規化。
- レスポンス例（フィールド取得・抜粋）:
  ```json
  {
    "count": 2,
    "value": [
      {"id": 9001, "fields": {
        "System.Title": "ログイン不可", "System.State": "Closed",
        "System.CreatedDate": "2026-05-02T09:00:00Z",
        "Microsoft.VSTS.Common.ClosedDate": "2026-05-06T15:00:00Z"}},
      {"id": 9002, "fields": {
        "System.Title": "表示崩れ", "System.State": "Active",
        "System.CreatedDate": "2026-05-03T10:00:00Z"}}
    ]
  }
  ```
