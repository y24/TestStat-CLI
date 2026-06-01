# TestStat Server

FastAPI backend for receiving and storing TestStat CLI progress reports.

## 前提条件

- Python 3.10 以上
- PostgreSQL がインストール済みで起動していること

## セットアップ手順

### 1. 仮想環境の作成とライブラリのインストール

```powershell
cd teststat-server
python -m venv .venv
.\.venv\Scripts\activate
pip install .
```

### 2. `.env` の作成

`.env.example` をコピーして実際の値に書き換える。

```powershell
copy .env.example .env
```

`.env` を開いて `your_password` を実際の PostgreSQL パスワードに変更する。**`DB_PASS` と `DATABASE_URL` の両方を変更すること。**

```
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=your_password          ← 変更
DB_NAME=teststat_db
MAINTENANCE_DB=postgres
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/teststat_db  ← 変更
```

### 3. データベースの作成

```powershell
python setup_db.py
```

`MAINTENANCE_DB` に接続して `DB_NAME` のデータベースを作成する。すでに存在する場合はスキップされる。

### 4. テーブルの作成（マイグレーション）

```powershell
.\migrate_db.ps1
```

### 5. 動作確認

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 18000
```

`http://localhost:18000/health` にアクセスして以下が返れば正常。

```json
{"status": "ok", "db": "connected"}
```

Swagger UI は `http://localhost:18000/docs` で確認できる。

## サーバー起動（通常運用）

```powershell
.\run_server.bat
```

Windows Server のタスクスケジューラに登録してスタートアップ時に自動起動させる。

- **トリガー**: スタートアップ時
- **操作**: `run_server.bat` のフルパスを指定
- **全般**: 「ユーザーがログオンしているかどうかにかかわらず実行する」を選択

## Azure DevOps 連携

プロジェクト新規作成時に Testing ID（= Azure DevOps の Work Item ID）から、プロジェクト名・テスト期間の開始日／終了日を自動取得する。**読み取り専用**で、Azure DevOps 側を更新することはない。

接続設定は `.env`、認証トークン（PAT）は **環境変数 `AZURE_DEVOPS_PAT`** で渡す。`AZURE_DEVOPS_USE_MOCK=true` の場合は実接続せずモックデータを返すため、接続できない環境でも動作確認できる。

### 1. Personal Access Token（PAT）の発行

1. Azure DevOps にサインインし、右上のユーザー設定 →「Personal access tokens」を開く。
2. 「New Token」で作成する。
   - **Organization**: 連携対象の組織
   - **Scopes**: `Work Items` の **Read**（読み取りのみで十分）
   - **Expiration**: 運用に合わせて設定（期限切れに注意）
3. 表示されたトークン文字列を控える（再表示できないため）。

### 2. PAT を環境変数に設定（Windows Server）

PAT は `.env` やリポジトリに書かず、環境変数 `AZURE_DEVOPS_PAT` で渡す。

> **重要**: サーバーはタスクスケジューラの実行アカウントで起動するため、そのアカウントから読める環境変数である必要がある。確実なのは **システム環境変数（Machine）** として設定すること。

管理者権限の PowerShell で設定する。

```powershell
[Environment]::SetEnvironmentVariable("AZURE_DEVOPS_PAT", "＜発行したPAT＞", "Machine")
```

- 第3引数 `"Machine"` = システム環境変数（全アカウントで有効）。特定ユーザーだけにする場合は `"User"`。
- 設定は **新しいプロセスから反映**される。すでに起動しているサーバー（uvicorn）には反映されないため、**タスクスケジューラのタスクを停止→開始**して再起動する。確実に反映するにはサーバー再起動が安全。
- `setx` でも設定できるが、コマンド履歴や画面に PAT が残るため `SetEnvironmentVariable` を推奨。

設定確認（新しい PowerShell を開いてから実行。同一セッションには即時反映されない）:

```powershell
[Environment]::GetEnvironmentVariable("AZURE_DEVOPS_PAT", "Machine")
```

> **セキュリティ**: PAT は機密情報。`.env`・Git・ログに残さない。アクセス権を絞った運用アカウントを使い、不要になったら Azure DevOps 側で失効させる。

### 3. `.env` に接続設定を追加

`.env`（`.env.example` 参照）に以下を設定する。

```
AZURE_DEVOPS_USE_MOCK=false          # 実接続。動作確認・オフライン時は true
AZURE_DEVOPS_ORGANIZATION=your-org   # dev.azure.com/{ここ}
# AZURE_DEVOPS_PROJECT=              # 省略可（Work Item ID は Org 単位で一意）
AZURE_DEVOPS_API_VERSION=7.1
AZURE_DEVOPS_TITLE_FIELD=System.Title
AZURE_DEVOPS_START_DATE_FIELD=Microsoft.VSTS.Scheduling.StartDate
AZURE_DEVOPS_END_DATE_FIELD=Microsoft.VSTS.Scheduling.FinishDate
```

- `AZURE_DEVOPS_ORGANIZATION`: 組織名（`https://dev.azure.com/{org}` の `{org}`）。
- 日付フィールドはプロセステンプレートに合わせて変更する（Agile/CMMI は既定値のままでよいことが多い。カスタムの場合は `Custom.ActualStartDate` のような参照名を指定）。
- 設定変更後はサーバーを再起動する。

### 4. 動作確認

モックモード（`AZURE_DEVOPS_USE_MOCK=true`）:

```powershell
curl http://localhost:18000/api/v1/azure-devops/work-items/1001
```

`{"work_item_id":1001,"name":"[MOCK] Work Item 1001","start_date":"2026-05-01","end_date":"2026-06-30"}` のような固定値が返れば正常。

実接続（`AZURE_DEVOPS_USE_MOCK=false`）:

```powershell
curl http://localhost:18000/api/v1/azure-devops/work-items/＜実在するWork Item ID＞
```

```json
{"work_item_id": 12345, "name": "サンプルプロジェクト", "start_date": "2026-05-01", "end_date": "2026-06-30"}
```

| 状態 | 意味・対処 |
|------|-----------|
| `200` | 正常。`name` / `start_date` / `end_date` を返す（日付フィールドに値が無ければ `null`） |
| `404` | Work Item が存在しない、または ID 誤り |
| `503` | `AZURE_DEVOPS_PAT` または `AZURE_DEVOPS_ORGANIZATION` が未設定。環境変数がサーバープロセスに渡っているか確認し、タスクを再起動 |
| `502` | PAT の権限不足・期限切れ、または Azure DevOps への接続失敗 |

### トラブルシュート

- **503 が返る / PAT が読めていない**: `AZURE_DEVOPS_PAT` をシステム環境変数（Machine）として設定したうえで、タスクスケジューラのタスクを再起動（必要ならサーバー再起動）。実行アカウントから環境変数が見えているかを確認する。
- **502（認証エラー）**: PAT の期限切れ・スコープ不足。`Work Items: Read` を付与して再発行する。
- **日付が `null` になる**: `AZURE_DEVOPS_*_DATE_FIELD` の参照名が対象 Work Item のフィールドと一致していない、または Work Item にその日付が未入力。プロセステンプレートのフィールド参照名を確認する。

## IIS 配下の仮想ディレクトリで公開する場合

1. IIS に以下の機能をインストールする。
   - Application Request Routing
   - URL Rewrite
2. IIS マネージャーでサーバー全体の `Application Request Routing Cache` を開き、`Server Proxy Settings...` から `Enable proxy` を有効にする。
3. 対象サイト配下に `tstat` という仮想ディレクトリまたはアプリケーションを作成する。
4. `tstat` 配下に URL Rewrite の受信規則を作成する。
   - Pattern: `(.*)`
   - Action type: `Rewrite`
   - Rewrite URL: `http://127.0.0.1:18000/{R:1}`
   - `Append query string`: 有効
5. バックエンドは通常どおり `http://127.0.0.1:18000` で起動する。

動作確認:

```powershell
curl http://hostname/tstat/health
curl -X POST http://hostname/tstat/api/v1/progress
```

## アップデート手順

```powershell
git pull
pip install .      # 依存ライブラリの追加があった場合
.\migrate_db.ps1   # スキーマ変更があった場合
# タスクスケジューラからサーバーを再起動
```

## マイグレーションファイルの新規作成

スキーマ変更を加えた際は以下で Alembic マイグレーションファイルを生成する。

```powershell
.\migrate_db.ps1 -Message "add_field_xxx"
```
