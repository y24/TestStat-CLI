# 識別子へのSharePoint URL登録 → tstat定期自動収集 改修計画

フロントの「識別子（label）の追加・編集」画面で SharePoint の共有 URL を登録できるようにし、サーバー側で `teststat-cli` の `tstat` コマンドを使って、その **TestingID・識別子・URL** に対応するファイルを定期的に自動収集（ダウンロード→集計→進捗送信）できるようにする。定期実行は **Windows Server のタスクスケジューラ**で行う。

- 作成日: 2026-06-22
- 対象リポジトリ: `teststat-frontend`（Vite + React + TS）, `teststat-server`（FastAPI）, `teststat-cli`（収集本体）
- 前提（既存資産の踏襲）:
  - `teststat-cli` は既に **リストファイル(YAML) の `files[].path` に SharePoint 共有 URL を書くと、実行時に Graph `/shares` 経由で一時 DL → 集計 → `/api/v1/progress` へ送信**できる（[`docs/sharepoint_remote_list_plan.md`](./sharepoint_remote_list_plan.md)、`utils/RemoteSource.py`）。
  - 識別子は `plan_labels`（`testing_id` × `label` 一意）で管理済み（`20260622_0016_add_plan_labels.py`）。
  - 認証は SharePoint 取得時の `az account get-access-token` に委譲（追加依存ゼロ方針）。

---

## 1. 目的とスコープ

### やりたいこと（要件）

1. **識別子の追加/編集画面に「SharePoint 共有 URL」欄を追加**し、`(testing_id, label)` ごとに 1 つの URL を保存する。
2. サーバー側に **収集コア（コレクターサービス）** を新設し、DB の `plan_labels` から URL 付きの識別子を読み出し、`testing_id` ごとに tstat 用リスト YAML を生成して **`tstat -l <list.yaml>` を実行**する。tstat が SharePoint からファイルを一時 DL → 集計 → `/api/v1/progress` へ送信する。
3. このコレクターサービスを **2 つの入り口から起動できる**ようにする:
   - **API**: `POST /api/v1/collect`（全件）/ `POST /api/v1/projects/{testing_id}/collect`（単一）を叩くと集計が走る。
   - **バッチ**: `collect.bat`（タスクスケジューラから定期実行）。バッチはコレクターサービスを直接呼ぶか、API を叩くかを選べる。
4. これにより、**タスクスケジューラによる定期実行**と、**任意タイミングの API 起動**（フロントの「今すぐ収集」ボタン、運用ツール、CI 等）の両方で最新実績を更新できる。

### スコープ外（今回やらないこと）

- 1 識別子に複数 URL／フォルダ URL の対応（Graph `/shares` は単一 driveItem 解決のため **1 識別子 = 1 ファイル URL**）。複数ファイルが要るテストは識別子を分ける運用で対応。
- 識別子ごとのシート/環境オーバーライド（`target_sheets` 等）。当面は `config.json` の既定値を使う。将来拡張余地として後述。
- 集計ジョブの永続的なキュー管理・進捗トラッキング画面（今回は「起動して 202 を返し、結果はログ＋最終実行ステータスで確認」程度に留める。本格的なジョブ管理は将来拡張）。
- tstat 本体の SharePoint 取得ロジックの変更（既存のまま再利用する）。

### 基本方針

- **単一の真実 = DB の `plan_labels`**。リスト YAML は収集のたびに DB から自動生成し、使い捨てる（手書き YAML を恒久管理しない）。
- **コレクターはコアを 1 つに集約し、API・バッチの両入り口から共有する**（`app/services/collector.py`）。ロジックを二重化しない。
- **tstat の契約は変えない**: 「YAML を渡せば収集して送信する」という既存インターフェースをそのまま使う。サーバーは YAML 生成と tstat 起動の **オーケストレーションのみ**を担う。
- **API 起動は非同期（バックグラウンド）を基本**とし、即座に `202 Accepted` を返す。集計（Graph 呼び出し・DL）に時間がかかってもリクエストをブロックしないようにする。
- **認証は既存どおり `az`（Graph トークン）**。API/バッチを実行するプロセスが Graph トークンを取得できることが前提（§8 で詳述）。

---

## 2. 全体構成

```
[ブラウザ / teststat-frontend]
   識別子の追加/編集画面
     ├ 識別子(label)            ─┐
     └ SharePoint 共有 URL       │  POST/PATCH /api/v1/.../plan-labels
                                  ▼
[teststat-server / FastAPI]
   routers/plan.py → crud/plan.py → DB: plan_labels(testing_id, label, source_url)

──────────────（ここまで登録。ここから集計の起動）──────────────

  入り口①: API                          入り口②: バッチ（定期実行）
  POST /api/v1/collect                   [Windows タスクスケジューラ]
  POST /api/v1/projects/{id}/collect          │ 定期起動
        │                                      ▼
        │ BackgroundTask                  collect.bat ──┬─ 直接呼び（server venv）
        ▼                                                └─ or  API を叩く（Invoke-WebRequest）
        └──────────────┬───────────────────────────────────┘
                       ▼
        [teststat-server / app/services/collector.py]  ← 共通コア・server venv（DB アクセス可）
           ① DB から source_url 付き plan_labels を取得し testing_id ごとにグループ化
           ② testing_id ごとに リスト YAML を一時生成
           ③ subprocess で  tstat -l <list.yaml>  を起動（testing_id ごとに 1 回）
                │
                ▼
        [teststat-cli / tstat]
           RemoteSource: az でトークン取得 → Graph /shares で一時DL → 集計
                │  reporting_api.base_url（= この server）
                ▼
        [teststat-server] POST /api/v1/progress  → DB 洗替（既存フロー）
                │
                ▼
           PB図・進捗一覧に反映
```

ポイント:
- **コレクターのコアは 1 つ**（`app/services/collector.py`）。API ルーター・バッチスクリプトの両方がこれを呼ぶ。
- コレクターは **DB アクセスが必要なので server 側の venv で動く**。tstat の起動は **subprocess**（tstat 側 venv の Python / インストール済み `tstat`）で行い、2 プロジェクトの依存を混ぜない。
- API 起動時、tstat は集計結果を **同じ server の `/api/v1/progress` にループバック POST** する。collect 処理を **イベントループをブロックしない形（BackgroundTasks / threadpool / `asyncio` サブプロセス）**で走らせ、子 tstat からの POST を捌けるようにする（§6・§10 参照）。

---

## 3. データモデル変更（`teststat-server`）

### 3.1 テーブル

`plan_labels` に **`source_url`（NULL 可）** を追加する。

| 列 | 型 | 説明 |
|---|---|---|
| `source_url` | `VARCHAR(2048)` NULL | SharePoint 共有 URL。未設定（NULL/空）の識別子は自動収集の対象外。 |

- 長さは共有 URL が 255 を超えるため `2048`。
- 既存の一意制約 `uq_plan_labels_testing_label`（`testing_id, label`）は維持。`source_url` には一意制約を付けない（別識別子が同一ファイルを参照する余地を残す）。

### 3.2 マイグレーション

新規 Alembic リビジョン `20260622_0017_add_source_url_to_plan_labels.py` を追加（既存 `..._0016` は変更しない＝適用済み環境を壊さない）。

```python
def upgrade() -> None:
    op.add_column("plan_labels", sa.Column("source_url", sa.String(length=2048), nullable=True))

def down_revision = "20260622_0016"
```

> DB 書き込み（`alembic upgrade`）は **ユーザーが実行**する。サーバー再起動も手動（`AGENTS.md` / メモリ `teststat-server-restart` 準拠）。

### 3.3 モデル / スキーマ / CRUD

- `app/models/plan.py` `PlanLabel`: `source_url: Mapped[str | None] = mapped_column(String(2048))` を追加。
- `app/schemas/plan.py`:
  - `PlanLabelCreate`: `source_url: str | None = Field(None, max_length=2048)` を追加。`field_validator` で **空文字 → None 正規化**、値があれば **`http://` / `https://` で始まること**を検証（不正値の混入防止）。
  - `PlanLabelUpdate`: 同上（`PlanLabelCreate` を継承のまま）。
  - `PlanLabelItem`: `source_url: str | None` を追加。
- `app/crud/plan.py`: `create_plan_label` / `update_plan_label` で `source_url` を保存・更新する。`update_plan_label` は現状 `label` 同一なら早期 return しているため、**`source_url` だけ変わったケースも更新**されるよう分岐を見直す。

---

## 4. フロントエンド変更（`teststat-frontend`）

### 4.1 型・API クライアント

- `src/api/types.ts`:
  - `PlanLabelItem` に `source_url: string | null`。
  - `PlanLabelCreatePayload` に `source_url?: string | null`（`PlanLabelUpdatePayload` は別名のまま継承）。
- `src/api/client.ts`: 関数シグネチャ変更なし（payload 型が拡張されるのみ）。

### 4.2 画面

- `PlanLabelCreateScreen.tsx` / `PlanLabelEditScreen.tsx`:
  - 識別子入力の下に **「SharePoint 共有 URL（任意）」**テキスト入力を追加。
  - `sourceUrl` / `onSourceUrlChange` を props 追加。
  - プレースホルダに「`https://contoso.sharepoint.com/:x:/s/...`（『リンクのコピー』で取得した共有 URL）」を表示。
  - 簡易バリデーション（任意・空 OR `http(s)://` 始まり）。最終検証はサーバー側。
- `PlanEditor.tsx`:
  - state `sourceUrlInput` を追加。識別子追加/編集の開始時に初期化（編集時は `editingPlanLabel.source_url ?? ''`）。
  - `submitPlanLabel` / `submitPlanLabelEdit` の payload に `source_url`（空→`null`）を含める。
  - 変更検知（`onDirtyChange`）に URL 変更も含める（編集時は label or source_url のどちらか変われば dirty）。
- 一覧（`PlanVersionTable.tsx` / `PlanListScreen.tsx`）: 任意で「URL 登録済み」アイコン表示（リンクアイコン）。必須ではない。

---

## 5. コレクター設計（`teststat-server`）

### 5.1 配置

```
teststat-server/
  app/
    services/collector.py   # 【共通コア】DB→YAML→tstat 起動。API・バッチが共有
    routers/collect.py      # API 入り口（BackgroundTasks で collector を起動）
    schemas/collect.py      # collect レスポンス（CollectResult / CollectStarted）
  scripts/
    collect_labels.py       # バッチ入り口（薄いエントリポイント。collector を直接呼ぶ）
  collect.bat               # タスクスケジューラから呼ぶラッパ（venv activate + 実行 + ログ）
```

**コアは `app/services/collector.py` に集約**し、2 つの入り口（API ルーター / バッチスクリプト）はこれを呼ぶだけにする。YAML 生成・グルーピング・tstat 起動ロジックを二重化しない。

### 5.2 コア API（サービス関数）

```python
# app/services/collector.py
def collect_all(db, *, settings) -> CollectResult: ...
def collect_project(db, testing_id, *, settings) -> CollectResult: ...
```

- `collect_all`: `source_url` 付き全 `plan_labels` を testing_id ごとにまとめて順次収集。
- `collect_project`: 単一 testing_id のみ収集（API の単一エンドポイント／部分再実行用）。
- 戻り値 `CollectResult`: `{ targets: int, succeeded: [testing_id...], failed: [{testing_id, reason, message}...], auth_error: bool, started_at, finished_at }`。ログにも同内容を残す。
  - `failed[].reason` は `"auth"`（認証失効）/ `"download"` / `"aggregate"` / `"report"` / `"other"` を区別。tstat の `--json` 出力（`warnings` / `reporting_api` / `error`）を解析して分類する（§8.2）。
  - いずれかの testing_id で認証失効を検知したら `auth_error: true` を立てる。

### 5.3 処理フロー（コア共通）

1. `app.database.SessionLocal` で DB セッション取得。
2. `source_url` が非 NULL/非空の `plan_labels` を取得（`collect_project` は対象 testing_id で絞る）。`Project.archived` は除外。
3. `testing_id` ごとにグループ化し、対応する `Project.name` を `project_name` として **リスト YAML** を生成（5.4）。一時ディレクトリへ書き出す。
4. `testing_id` ごとに **`tstat -l <list.yaml>` を subprocess 実行**（`--json` で結果を取り込みログ化）。
   - tstat が SharePoint DL → 集計 → `/api/v1/progress` 送信まで完結。
5. 各 testing_id の成否・件数を `CollectResult` に集約し、ログファイルにも記録。一部失敗しても **他 testing_id は継続**（tstat 内でも 1 ファイル失敗はスキップ継続）。
6. 一時ディレクトリを削除。バッチの終了コードは「全失敗=1 / それ以外=0」。

### 5.4 生成する YAML（`testing_id` 単位）

```yaml
project:
  project_name: <Project.name>
  testing_id: <testing_id>
  files:
    - label: <plan_labels.label>
      path: "<plan_labels.source_url>"   # SharePoint 共有 URL
    - label: <別の識別子>
      path: "<その URL>"
```

- `path` に共有 URL を直接書く（tstat 側で `is_remote_path` 判定 → 一時 DL）。
- `subtask_id` は今回未使用（WBS 連携が要る場合の将来拡張）。
- シート/環境は付けない（`config.json` 既定を使用）。

### 5.5 tstat の起動方法と設定

サーバーから tstat をどう呼ぶかを **設定（`.env`）で解決**する。tstat は別 venv のため、フルパス指定を基本とする。

| 環境変数 | 既定 | 説明 |
|---|---|---|
| `COLLECT_ENABLED` | `true` | コレクター有効/無効（API・バッチ共通）。 |
| `TSTAT_COMMAND` | （必須） | tstat 実行コマンド。例: `D:\Script\TestStat-CLI\teststat-cli\.venv\Scripts\python.exe D:\Script\TestStat-CLI\teststat-cli\test_stat_cli.py`、またはインストール済みなら `tstat`。 |
| `TSTAT_CONFIG` | 空 | tstat の `--config` に渡す config.json パス（省略時 tstat 既定）。`reporting_api.base_url` と `sharepoint.enabled` がここで効く。 |
| `COLLECT_WORK_DIR` | OS 一時 | リスト YAML を書き出す作業ディレクトリ。 |
| `COLLECT_LOG_DIR` | `teststat-server/logs` | 実行ログの出力先。 |
| `COLLECT_TIMEOUT_SEC` | `600` | testing_id 1 件あたりの subprocess タイムアウト。 |

- tstat 側 `config.json` の `reporting_api.base_url` は **この server**（例 `http://localhost:18000`）を指す必要がある。
- `TSTAT_COMMAND` は文字列を `shlex` 風に分割して `subprocess.run([...])` に渡す（`shell=False`）。

---

## 6. API 入り口（`teststat-server`）

「叩いたら集計が走る」入り口。コア（`collector.py`）を **BackgroundTasks で起動**し、即座に `202 Accepted` を返す。

### 6.1 エンドポイント

| メソッド / パス | 説明 | レスポンス |
|---|---|---|
| `POST /api/v1/collect` | URL 登録済み全識別子を収集（全 testing_id）。 | `202` `CollectStarted { started: true, targets: <件数> }` |
| `POST /api/v1/projects/{testing_id}/collect` | 単一プロジェクトのみ収集。 | `202` `CollectStarted { started: true, targets: <件数> }` |
| `GET /api/v1/collect/status` | 最終実行の結果サマリ（任意・軽量）。**`auth_error` を含み認証失効が一目で分かる**（§8.2）。 | `200` `CollectResult`（最後の実行内容）。 |

- ルーター `app/routers/collect.py` を新設し `main.py` に `include_router`。
- 実装イメージ:
  ```python
  @router.post("/collect", status_code=202)
  def post_collect(background: BackgroundTasks, db: Session = Depends(get_db)):
      if not settings.collect_enabled:
          raise HTTPException(503, "collector disabled")
      targets = count_collect_targets(db)        # 軽い件数確認のみ同期
      background.add_task(run_collect_all)        # 実処理は別セッションで非同期
      return {"started": True, "targets": targets}
  ```
- **非同期化のポイント**: `BackgroundTasks` 内では **新しい DB セッションを開く**（リクエストの `Depends(get_db)` セッションはレスポンス後に閉じるため使い回さない）。tstat の subprocess 待ちはイベントループを塞がないよう `asyncio.create_subprocess_exec` か `run_in_threadpool` を用いる。
- **多重実行ガード**: 収集中フラグ（プロセス内 `asyncio.Lock` / 単純フラグ。マルチワーカー運用ならファイルロック or DB ロック）。実行中に再度叩かれたら `409 Conflict` で弾く。
- **同期版が必要なら**: `?wait=true` で完了まで待って `CollectResult` を返すオプションも検討可（CI 等で結果を見たいケース）。既定は非同期。

### 6.2 フロントの「今すぐ収集」ボタン（任意）

- 識別子一覧 or PB図パネルに「今すぐ収集」ボタンを置き、`POST /api/v1/projects/{testing_id}/collect` を叩く。
- 押下後は「収集を開始しました（数分後に反映）」を表示。完了検知は `actuals_updated_at` のポーリング or 再読込で代替（本格的な進捗表示はスコープ外）。

---

## 7. tstat 連携の流れ（既存フローの確認）

リスト YAML を渡された tstat は以下を実行する（`test_stat_cli.py` 既存ロジック）:

1. `files[].path` が URL → `RemoteSource.RemoteFileManager.fetch()` で一時 DL（`az` トークン → Graph `/shares/{shareId}/driveItem` → 署名付き URL DL）。`atexit` で一時ディレクトリ削除。
2. 集計（`ReadData.aggregate_results`）。
3. `args.list` 経由なので `reporting_api.enabled` なら `build_progress_payload` → `send_progress` で **`/api/v1/progress` に POST**。`testing_id` ごとに洗替。
4. アーカイブ済みプロジェクトは送信スキップ（既存 `_get_project_status` ガード）。

→ コレクターは **YAML を生成して tstat を起動するだけ**で、ダウンロード・集計・送信は既存資産が担う。

---

## 8. 認証（`az login` の再利用）

**方針: 既存 TestStat-CLI の `az login` 前提をそのまま使う。** 本改修で新しい認証方式は作らない。SharePoint 取得は `az account get-access-token --resource https://graph.microsoft.com`（`RemoteSource.get_access_token`）に委譲され、`az login` 済みなら追加実装なしで通る。

> サービスプリンシパル等は **任意の将来強化**であり今回は対象外。`az login` のみ考慮する。

### 8.1 唯一の前提: 実行アカウントの一致

`az login` のトークンは **ログインした Windows ユーザー固有**（`%USERPROFILE%\.azure`）に保存される。よって **tstat を起こす親プロセスが、その `az login` 済みユーザーで動いていること**だけが前提。

- **バッチ入り口**: タスクスケジューラを **`az login` 済みユーザー**で「ログオン状態に関わらず実行」に設定する。別のサービスアカウントで動かすと `.azure` が見えず失敗する。
- **API 入り口**: `az` を呼ぶのは tstat を subprocess する **server(uvicorn) プロセス**。よって **server を起動しているアカウント**が `az login` 済みである必要がある（手動 tstat 実行時と「ログイン主体」が変わる点に注意）。

開発・検証は `TESTSTAT_SHAREPOINT_MOCK`（ローカル xlsx パス）で **az/Graph なしの全経路ドライラン**が可能（§9 で活用）。

### 8.2 トークン失効を必ず可視化する

無人実行ではトークン失効（期限・MFA・条件付きアクセス）で**黙って失敗**するのが最大の運用リスク。これを「分かる」ようにするための考慮を入れる。

`RemoteSource` は失効時に明確なメッセージで `RemoteSourceError` を投げる（例:「Azure にログインしていません。`az login` を実行してください。」、403「アクセス権がありません」）。tstat はこれを警告／レポート失敗として `--json` 出力に載せる。コレクターはこれを拾って以下を行う:

- **認証失敗を専用フラグで区別**: コレクターが tstat の `--json` 出力（`warnings` / `reporting_api` / `error`）を解析し、`az login` / ログイン未 / 401 / 403 等のパターンを検知したら、`CollectResult.failed[].reason = "auth"`（＋原文メッセージ）として **「集計失敗」ではなく「認証失効」と明示**する。
- **`GET /api/v1/collect/status`** が最終実行の `CollectResult` を返すので、**画面・運用ツールから「認証切れで止まっている」と即座に判別**できる。`status` に `auth_error: true` のサマリフラグを持たせる。
- **ログに明示**: `COLLECT_LOG_DIR` のログ先頭/末尾に `AUTH ERROR: az login required` を分かりやすく出力。バッチの終了コードも認証失敗時は専用値（例 `2`）にして、タスクスケジューラの「前回の実行結果」で気づけるようにする。
- **（任意・将来）通知**: 認証失敗時にメール/Webhook 通知。今回は「可視化」までをスコープとし、通知は将来拡張。

> ポイント: 失効しても**サイレントに古い実績のまま放置されない**こと。`collect/status` とログと終了コードの 3 点で必ず気づける状態にする。

---

## 9. フェーズ分割・作業手順

### フェーズ A: バックエンド（データモデル＋識別子 API）
1. Alembic `..._0017_add_source_url_to_plan_labels.py` 追加（ユーザーが `upgrade` 実行）。
2. `models/plan.py` / `schemas/plan.py` / `crud/plan.py` に `source_url` 反映（空→None・http(s) 検証）。
3. `tests/test_plan_crud.py` 拡張: 作成/更新/取得で `source_url` 往復、不正 URL 422、`source_url` のみ変更の更新。
4. サーバー再起動（ユーザー）。

### フェーズ B: フロントエンド（登録 UI）
5. `types.ts` 拡張。
6. `PlanLabelCreateScreen` / `PlanLabelEditScreen` に URL 欄追加。
7. `PlanEditor` に state/payload/dirty 連携。
8. `npm run build`（型チェック）。手動で登録→保存→再取得を確認。

### フェーズ C: コレクターコア
9. `app/services/collector.py`（YAML 生成・グルーピング・tstat subprocess 起動・`CollectResult` 集約）。
10. `.env` 設定項目（`COLLECT_*` / `TSTAT_*`）を `config.py` に追加。
11. ユニットテスト: YAML 生成（fake な label 行→期待 YAML）、tstat コマンド分割、無効 URL/アーカイブ除外。

### フェーズ D: 入り口（API＋バッチ）
12. **API**: `app/schemas/collect.py` ＋ `app/routers/collect.py`（`POST /collect` / `POST /projects/{id}/collect` / `GET /collect/status`）を追加し `main.py` に登録。BackgroundTasks 化・多重実行ガード。
13. **バッチ**: `scripts/collect_labels.py`（薄いエントリ、collector を直接呼ぶ）＋ `collect.bat`。
14. **ドライラン**: `TESTSTAT_SHAREPOINT_MOCK` を設定し、(a) `POST /api/v1/collect` を叩く / (b) `collect.bat` 手動実行 の両経路で `/api/v1/progress` 反映 → PB図確認。

### フェーズ E: タスクスケジューラ・ドキュメント
15. `schtasks` 登録手順 / 実行アカウント / 頻度 / ログ / 認証（§8）を `docs/windows_server_task_scheduler_setup.md`（新規）に記載。バッチが「直接呼び」か「API を叩く」かの選択も記載。
16. `list_sample.yaml` / README / 本計画の「状態」を更新。

---

## 10. タスクスケジューラ設定（概要）

バッチの入り口は **2 方式**から選べる。

**方式①: collector を直接呼ぶ**（server プロセスに依存せず、バッチアカウントで完結）

```bat
:: collect.bat（直接呼び）
@echo off
cd /d D:\Script\TestStat-CLI\teststat-server
call .venv\Scripts\activate.bat
:: 前提: このバッチ実行アカウントで事前に `az login` 済みであること（§8.1）
python -m scripts.collect_labels >> logs\collect_%date:~0,4%%date:~5,2%%date:~8,2%.log 2>&1
```

**方式②: API を叩く**（起動中の server に集計させる。バッチは薄い）

```bat
:: collect.bat（API 起動）
@echo off
powershell -Command "Invoke-WebRequest -Method POST -Uri http://localhost:18000/api/v1/collect -UseBasicParsing" ^
  >> D:\Script\TestStat-CLI\teststat-server\logs\collect_%date:~0,4%%date:~5,2%%date:~8,2%.log 2>&1
```

`schtasks` 登録例（毎時実行・ログオン状態に依存しない）:

```
schtasks /Create /TN "TestStat\CollectLabels" /TR "D:\Script\TestStat-CLI\teststat-server\collect.bat" ^
  /SC HOURLY /RU <実行アカウント> /RP * /RL HIGHEST /F
```

- **実行アカウント**: §8.1 参照。方式①はバッチ実行アカウント、方式②は **server を起動しているアカウント**が `az login` 済みである必要がある。
- **頻度**: 既定は毎時。負荷・更新頻度に応じて調整（識別子数 × Graph 呼び出し）。
- **多重起動防止**: タスク設定「既に実行中なら新しいインスタンスを開始しない」＋ API 側の多重実行ガード（§6.1）の二重で守る。

---

## 11. リスク・考慮事項

- **認証失効（§8）**: 最大のリスク。`az login` のトークン切れで無言停止しないよう、`CollectResult.auth_error`・`GET /collect/status`・ログ・バッチ終了コードの 4 点で**必ず気づける**ようにする（§8.2）。再ログインで復旧。通知は将来拡張。
- **API のループバックとブロッキング**: API 入り口では server → tstat subprocess → server `/api/v1/progress` と同一 server へ戻る。collect 処理を **必ず非同期（BackgroundTasks/threadpool/async subprocess）**にし、シングルワーカーでも子 POST を捌けるようにする。同期実装にすると自己デッドロック的に詰まり得る。
- **長い URL**: `source_url` 列長 2048。SharePoint 共有 URL は通常収まるが、極端に長い場合は要再検討。
- **tstat と server の config 不整合**: tstat 側 `reporting_api.base_url` が server を指していないと送信されない。`TSTAT_CONFIG` で明示。
- **同時実行と DB 洗替**: tstat の `/api/v1/progress` は testing_id 単位の洗替。API とスケジューラ、手動 tstat が同時に走ると最後勝ち。多重実行ガード＋タスク設定で重複を避ける。
- **アーカイブ済み**: collector が YAML 生成時に `Project.archived` を除外（既存の送信ガードと二重）。
- **1 識別子 = 1 ファイル**: フォルダ/複数ファイルは非対応。要件が出たら識別子分割 or YAML 複数 files で対応。

---

## 12. 受け入れ条件（Done の定義）

- [ ] 識別子の追加/編集画面で SharePoint URL を登録・更新・クリアでき、再読込で保持される。
- [ ] 不正 URL（http(s) 以外）は 422 で拒否される。
- [ ] `POST /api/v1/collect` / `POST /api/v1/projects/{id}/collect` を叩くと集計が走り（202 即時応答・非同期）、モックモードで実績が `/api/v1/progress` 経由で更新され PB図に反映される。
- [ ] `collect.bat`（直接呼び・API 起動の両方）で同じ収集が実行できる。
- [ ] タスクスケジューラ登録で定期実行され、ログ／`GET /collect/status` に各 testing_id の成否が残る。
- [ ] **`az login` のトークン失効時に、`GET /collect/status` の `auth_error`・ログ・バッチ終了コードのいずれからも「認証切れ」と判別できる**（サイレント失敗しない）。
- [ ] 実接続（`az login`）での疎通確認手順がドキュメント化されている。

---

## 状態

実装済み（2026-06-22）。DB マイグレーション適用と backend 手動再起動は運用者が実施する。タスクスケジューラ手順は [`docs/windows_server_task_scheduler_setup.md`](./windows_server_task_scheduler_setup.md) を参照。

