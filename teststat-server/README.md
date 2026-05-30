# TestStat Server

FastAPI backend for receiving and storing TestStat CLI progress reports.

## 前提条件

- Python 3.10 以上
- PostgreSQL がインストール済みで起動していること

## セットアップ手順

### 1. 仮想環境の作成とライブラリのインストール

```powershell
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
