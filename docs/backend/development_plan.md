# TestStat バックエンド開発計画

## 概要

TestStat CLI ツールで集計したテスト進捗データをサーバーへ送信・蓄積するためのバックエンド API とデータベースの開発計画。

- **バックエンド**: FastAPI + Uvicorn
- **DB**: PostgreSQL
- **マイグレーション**: Alembic
- **運用**: Windows Server タスクスケジューラで起動

---

## システム構成

```
[各メンバーの PC]
  tstat -l list.yaml
    └─ Excel 集計 → POST /api/v1/progress
                         │
                    [サーバー]
                    FastAPI (Uvicorn)
                         │
                    PostgreSQL
                         │
               [将来] ダッシュボード (フロントエンド)
```

---

## ディレクトリ構成

バックエンドは **別リポジトリ** として管理する想定。

```
teststat-server/
├── pyproject.toml          # pip install . でインストール
├── alembic.ini
├── run_server.bat          # 起動スクリプト（タスクスケジューラ用）
├── migrate_db.ps1          # マイグレーション実行スクリプト
├── setup_db.py             # DB・ユーザー作成スクリプト
├── .env.example            # 環境変数テンプレート
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
└── app/
    ├── __init__.py
    ├── main.py             # FastAPI アプリ定義・起動
    ├── config.py           # 環境変数読み込み (pydantic-settings)
    ├── database.py         # DB 接続・セッション管理
    ├── models/
    │   ├── __init__.py
    │   └── progress.py     # SQLAlchemy ORM モデル
    ├── schemas/
    │   ├── __init__.py
    │   └── progress.py     # Pydantic スキーマ（OpenAPI 定義）
    ├── crud/
    │   ├── __init__.py
    │   └── progress.py     # DB 操作（upsert ロジック）
    └── routers/
        ├── __init__.py
        └── progress.py     # エンドポイント定義
```

---

## CLI 側の変更点

### 1. YAML ファイルへの `testing_id` 追加

`project` 直下に整数の `testing_id` を追加する。**指定なしの場合はワーニングを表示して送信をスキップ**する（CLIの通常機能には影響しない）。

```yaml
project:
  project_name: サンプルプロジェクト
  testing_id: 1001          # 新規追加（必須・整数）
  subtask_id: 999
  files:
    - label: TEST001
      path: input_sample/sample1.xlsx
```

### 2. `config.json` への `reporting_api` セクション追加

```json
{
  "reporting_api": {
    "enabled": true,
    "base_url": "http://192.168.1.100:18000",
    "sender": "山田太郎"
  }
}
```

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `enabled` | - | `false` にすると送信を無効化（デフォルト `true`） |
| `base_url` | ○ | バックエンド API の URL |
| `sender` | - | 送信者名（省略可。未指定は `null`） |

### 3. 送信タイミング

- `-l` オプション（YAMLリスト指定）でのみ送信対象
- `testing_id` が指定されていない場合: `WARNING: testing_id が未設定のため進捗データの送信をスキップします` を表示
- 送信失敗は WARNING 扱い。CLI は正常終了する

---

## データベース設計

### テーブル: `testings`

testing_id ごとのプロジェクト情報。初回送信時に INSERT、以降は `updated_at` を更新。

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | SERIAL PK | |
| `testing_id` | INTEGER UNIQUE | YAML の `testing_id` |
| `project_name` | VARCHAR(255) | |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

### テーブル: `file_progress`

ファイル単位の進捗データ。送信時に `testing_id` が一致する全行を DELETE してから INSERT する。

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | SERIAL PK | |
| `testing_id` | INTEGER | testings.testing_id |
| `file_name` | VARCHAR(255) | ファイルのベース名 |
| `label` | VARCHAR(255) NULL | ラベル（識別子） |
| `environment` | VARCHAR(255) NULL | 環境名 |
| `total_cases` | INTEGER | 全件数 |
| `available_cases` | INTEGER | 対象件数（除外除く） |
| `excluded_cases` | INTEGER | 除外件数 |
| `completed` | INTEGER | 完了数 |
| `executed` | INTEGER | 消化数 |
| `not_run` | INTEGER | 未着手数 |
| `completed_rate` | FLOAT | 完了率 (%) |
| `executed_rate` | FLOAT | 消化率 (%) |
| `result_pass` | INTEGER | |
| `result_fixed` | INTEGER | |
| `result_fail` | INTEGER | |
| `result_blocked` | INTEGER | |
| `result_suspend` | INTEGER | |
| `result_na` | INTEGER | |
| `start_date` | DATE NULL | |
| `latest_update` | DATE NULL | |
| `sender` | VARCHAR(255) NULL | 送信者名 |
| `sent_at` | TIMESTAMP | 送信日時 |

### テーブル: `daily_progress`

日別の実施数データ（結果種別内訳あり）。送信時に `testing_id` が一致する全行を DELETE してから INSERT する。

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | SERIAL PK | |
| `testing_id` | INTEGER | |
| `file_name` | VARCHAR(255) | ファイルのベース名 |
| `label` | VARCHAR(255) NULL | ラベル（識別子） |
| `environment` | VARCHAR(255) NULL | |
| `date` | DATE | |
| `result_pass` | INTEGER | |
| `result_fixed` | INTEGER | |
| `result_fail` | INTEGER | |
| `result_blocked` | INTEGER | |
| `result_suspend` | INTEGER | |
| `result_na` | INTEGER | |
| `completed` | INTEGER | |
| `executed` | INTEGER | |
| `planned` | INTEGER NULL | |

### テーブル: `daily_person_progress`

担当者別・日別の実施数データ。送信時に `testing_id` が一致する全行を DELETE してから INSERT する。

CLIの `by_name` フィールド（`{date: {person: count}}` 構造）から生成。結果種別の内訳はなく実施数のみ。`daily_progress` とは別テーブルで管理する。

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | SERIAL PK | |
| `testing_id` | INTEGER | |
| `file_name` | VARCHAR(255) | ファイルのベース名 |
| `label` | VARCHAR(255) NULL | ラベル（識別子） |
| `environment` | VARCHAR(255) NULL | |
| `date` | DATE | |
| `person` | VARCHAR(255) | 担当者名 |
| `count` | INTEGER | 実施数（結果あり行の数） |

---

## API 設計

### ベース URL

```
/api/v1
```

### エンドポイント一覧

| メソッド | パス | 説明 |
|--------|------|------|
| `POST` | `/api/v1/progress` | CLI から進捗データを受信・保存 |
| `GET` | `/api/v1/progress/{testing_id}` | testing_id のサマリ取得 |
| `GET` | `/api/v1/progress/{testing_id}/files` | ファイル別進捗一覧 |
| `GET` | `/api/v1/progress/{testing_id}/daily` | 日別進捗一覧 |
| `GET` | `/api/v1/testings` | 全 testing_id の一覧 |
| `GET` | `/health` | ヘルスチェック |

---

### `POST /api/v1/progress` — 進捗データ送信

CLI が実行後に呼び出す。`testing_id` が一致する既存データを全削除してから再 INSERT する（洗替）。

**リクエストボディ**:

```json
{
  "testing_id": 1001,
  "project_name": "サンプルプロジェクト",
  "sender": "山田太郎",
  "sent_at": "2026-05-31T10:00:00",
  "files": [
    {
      "file_name": "sample1.xlsx",
      "label": "TEST001",
      "environment": "環境a",
      "total_cases": 100,
      "available_cases": 90,
      "excluded_cases": 10,
      "completed": 70,
      "executed": 80,
      "not_run": 10,
      "completed_rate": 77.78,
      "executed_rate": 88.89,
      "start_date": "2026-05-01",
      "latest_update": "2026-05-30",
      "results": {
        "Pass": 65,
        "Fixed": 5,
        "Fail": 5,
        "Blocked": 3,
        "Suspend": 2,
        "N/A": 0
      },
      "daily": [
        {
          "date": "2026-05-01",
          "Pass": 10,
          "Fixed": 0,
          "Fail": 2,
          "Blocked": 0,
          "Suspend": 0,
          "N/A": 0,
          "completed": 10,
          "executed": 12,
          "planned": null
        }
      ],
      "by_person": [
        {
          "date": "2026-05-01",
          "person": "山田太郎",
          "count": 8
        },
        {
          "date": "2026-05-01",
          "person": "田中花子",
          "count": 4
        }
      ]
    }
  ]
}
```

> `by_person` は CLI の `by_name` フィールド（`{date: {person: count}}`）を展開したリスト。  
> 担当者名が空の行は除外する。

**洗替前バリデーション**（いずれかに該当する場合は `422 Unprocessable Entity` を返し、DB は一切変更しない）:

- `files` が空リスト
- 全ファイルが `available_cases == 0`（読み取れたテストケースが 0 件）
- 全ファイルにエラーが含まれている（CLIがファイルを正常に処理できなかった）

バリデーションを通過した場合のみ洗替を実行する。

**洗替の処理順序**:
1. バリデーション通過を確認
2. `file_progress`、`daily_progress`、`daily_person_progress` から `testing_id` が一致する全行を DELETE
3. リクエストの全データを INSERT
4. `testings` テーブルを UPSERT（初回は INSERT、以降は `updated_at` を UPDATE）

**レスポンス** (`200 OK`):

```json
{
  "testing_id": 1001,
  "inserted_files": 3,
  "inserted_daily_rows": 45,
  "inserted_person_rows": 30
}
```

---

### `GET /api/v1/progress/{testing_id}` — サマリ取得

```json
{
  "testing_id": 1001,
  "project_name": "サンプルプロジェクト",
  "updated_at": "2026-05-31T10:00:00",
  "summary": {
    "total_cases": 300,
    "available_cases": 270,
    "completed": 200,
    "executed": 230,
    "completed_rate": 74.07,
    "executed_rate": 85.19
  },
  "results": {
    "Pass": 180,
    "Fixed": 20,
    "Fail": 15,
    "Blocked": 10,
    "Suspend": 5,
    "N/A": 0
  }
}
```

---

### `GET /api/v1/progress/{testing_id}/files` — ファイル別一覧

```json
[
  {
    "file_name": "sample1.xlsx",
    "label": "TEST001",
    "environment": "環境a",
    "total_cases": 100,
    "available_cases": 90,
    "completed": 70,
    "executed": 80,
    "completed_rate": 77.78,
    "executed_rate": 88.89,
    "start_date": "2026-05-01",
    "latest_update": "2026-05-30",
    "sender": "山田太郎",
    "sent_at": "2026-05-31T10:00:00"
  }
]
```

---

### `GET /api/v1/progress/{testing_id}/daily` — 日別一覧

```json
[
  {
    "date": "2026-05-01",
    "file_name": "sample1.xlsx",
    "label": "TEST001",
    "environment": "環境a",
    "completed": 10,
    "executed": 12,
    "Pass": 10,
    "Fixed": 0,
    "Fail": 2,
    "Blocked": 0,
    "Suspend": 0,
    "N/A": 0
  }
]
```

---

### `GET /api/v1/testings` — testing_id 一覧

```json
[
  {
    "testing_id": 1001,
    "project_name": "サンプルプロジェクト",
    "created_at": "2026-05-01T09:00:00",
    "updated_at": "2026-05-31T10:00:00"
  }
]
```

---

### `GET /health` — ヘルスチェック

```json
{
  "status": "ok",
  "db": "connected"
}
```

---

## 運用スクリプト

### `setup_db.py` — DB・ユーザー作成

初回セットアップ時に一度だけ実行するスクリプト。PostgreSQL に接続してデータベースとユーザーを作成する。

```
python setup_db.py
```

- `.env` を読み込んで接続情報を取得
- `MAINTENANCE_DB`（postgres）に接続し、`DB_NAME` が存在しない場合のみ CREATE DATABASE

### `migrate_db.ps1` — マイグレーション実行

Alembic マイグレーションを実行するラッパースクリプト。

```powershell
.\migrate_db.ps1            # alembic upgrade head を実行
.\migrate_db.ps1 -Message "add_field_xxx"  # 新規マイグレーション生成
```

### `run_server.bat` — サーバー起動

Windows Server タスクスケジューラから呼び出すためのバッチファイル。

```bat
@echo off
cd /d %~dp0
call .venv\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 18000 --workers 2
```

### 環境変数 (`.env.example`)

`.env.example` としてリポジトリに含め、実際の `.env` は各自でコピーして値を設定する。

```
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=your_password
DB_NAME=teststat_db
MAINTENANCE_DB=postgres
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/teststat_db
```

---

## 依存ライブラリ (`pyproject.toml`)

```toml
[project]
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "psycopg2-binary>=2.9.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
]
```

`pip install .` で全依存ライブラリをインストール可能にする。

---

## OpenAPI 管理方針

- FastAPI の自動生成 OpenAPI スキーマ (`/openapi.json`) を正とする
- Pydantic スキーマに `description`、`example` を記述して仕様を明示
- 開発中は `http://localhost:18000/docs` (Swagger UI) で確認

---

## 開発フェーズ

### Phase 1: バックエンド基盤（優先）

- [x] DB スキーマ設計・Alembic 初期マイグレーション
- [x] `POST /api/v1/progress` 実装（洗替ロジック）
- [x] `GET /api/v1/progress/{testing_id}/*` 実装
- [x] `GET /api/v1/testings` 実装
- [x] `GET /health` 実装
- [x] `setup_db.py` 作成
- [x] `migrate_db.ps1` 作成
- [x] `run_server.bat` 作成

### Phase 2: CLI 側の対応

- [x] `ProjectList.py`: YAML から `testing_id` を読み込む
- [x] `config.json`: `reporting_api` セクションのサポート
- [x] `ReportingClient.py`: API 送信クラスの実装
- [x] `test_stat_cli.py`: 集計後に `ReportingClient` を呼び出す処理を追加

### Phase 3: フロントエンド（将来）

- ダッシュボード（Vue.js / React 等）
- testing_id 別の進捗グラフ、日別バーンダウン表示
- ファイル別完了率テーブル

---

## 注意事項・設計判断

- **送信失敗は WARNING 扱い**: ネットワーク障害等で送信に失敗しても CLI は正常終了。ユーザーが気づけるよう WARNING メッセージは表示する。
- **洗替のスコープ**: `testing_id` が一致する全行を DELETE してから再 INSERT。**別の `testing_id` には影響しない**。
- **洗替前バリデーション**: 空リスト・全ファイルエラー・全ファイル 0 件の場合は `422` を返して既存データを保護する。DELETE と INSERT はトランザクションで囲み、INSERT 中にエラーが発生した場合もロールバックして既存データを維持する。
- **`testing_id` 未設定は WARNING**: `-l` オプション使用時に `testing_id` がなければ送信をスキップし、WARNING を表示する。
- **認証**: 初期実装では認証なし（LAN 内で運用する前提）。必要に応じて API キー認証を追加可能。
- **`results` フィールドのキー**: Pass/Fixed/Fail/Blocked/Suspend/N/A は `config.json` の `test_status.results` で定義されるため、サーバー側は固定カラムで保持する（現状の 6 種類で実装）。
