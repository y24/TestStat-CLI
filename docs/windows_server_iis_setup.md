# Windows Server IIS セットアップ手順

TestStat のフロントエンドを Windows Server の IIS で公開し、バックエンドを OS 起動時にタスクスケジューラから自動起動する手順です。

この手順では以下の構成を前提にします。

- リポジトリ配置先: `c:\app\TestStat`
- フロントエンド配信先: `c:\app\TestStat\teststat-frontend\dist`
- バックエンド起動 URL: `http://127.0.0.1:18000`
- 公開 URL: `http://<server-name>/tstat`

環境に合わせてパスやサイト名を読み替えてください。この手順では、IIS の既存サイト配下に `tstat` アプリケーションを作成し、その物理パスとして `teststat-frontend\dist` を指定します。

## 1. 事前準備

### 1.1 必要なソフトウェア

- Windows Server
- IIS
- IIS URL Rewrite
- IIS Application Request Routing (ARR)
- Node.js 20.19.0 以上、または 22.12.0 以上
- Python 3.10 以上
- PostgreSQL

### 1.2 IIS 機能の有効化

サーバーマネージャーで以下を有効にします。

- Web Server (IIS)
- Static Content
- Default Document
- HTTP Errors
- Request Filtering

PowerShell で有効化する場合は、管理者権限で実行します。

```powershell
Install-WindowsFeature Web-Server, Web-Static-Content, Web-Default-Doc, Web-Http-Errors, Web-Filtering -IncludeManagementTools
```

### 1.3 URL Rewrite と ARR のインストール

以下を IIS にインストールします。

- URL Rewrite
- Application Request Routing

インストール後、IIS マネージャーでサーバー全体の `Application Request Routing Cache` を開き、`Server Proxy Settings...` から `Enable proxy` を有効にします。

## 2. バックエンドのセットアップ

### 2.1 初期セットアップ

```powershell
cd c:\app\TestStat\teststat-server
python -m venv .venv
.\.venv\Scripts\activate
pip install .
copy .env.example .env
```

`.env` を開き、PostgreSQL 接続情報などをサーバー環境に合わせて設定します。

```powershell
python setup_db.py
.\migrate_db.ps1
```

### 2.2 起動確認

既存の起動用 bat を使います。

```powershell
cd c:\app\TestStat\teststat-server
.\run_server.bat
```

別の PowerShell から確認します。

```powershell
curl http://127.0.0.1:18000/health
```

`{"status":"ok","db":"connected"}` のようなレスポンスが返れば正常です。

## 3. タスクスケジューラでバックエンドを OS 起動時に実行

### 3.1 GUI で登録する場合

1. タスクスケジューラを開きます。
2. `タスクの作成...` を選択します。
3. `全般` タブを設定します。
   - 名前: `TestStat Backend`
   - `ユーザーがログオンしているかどうかにかかわらず実行する` を選択
   - `最上位の特権で実行する` を選択
   - 構成: 使用中の Windows Server バージョン
4. `トリガー` タブで `新規...` を選択します。
   - タスクの開始: `スタートアップ時`
   - 遅延時間を指定する場合: `30 秒` など
5. `操作` タブで `新規...` を選択します。
   - 操作: `プログラムの開始`
   - プログラム/スクリプト: `c:\app\TestStat\teststat-server\run_server.bat`
   - 開始: `c:\app\TestStat\teststat-server`
6. `条件` タブで、必要に応じて `コンピューターを AC 電源で使用している場合のみタスクを開始する` を外します。
7. `設定` タブを設定します。
   - `タスクを要求時に実行する` を有効
   - `タスクが失敗した場合の再起動の間隔`: `1 分`
   - `再起動試行の最大数`: `3 回`
8. 保存し、実行アカウントのパスワードを入力します。

登録後、タスクを右クリックして `実行する` を選び、`http://127.0.0.1:18000/health` で確認します。

### 3.2 schtasks コマンドで登録する場合

管理者権限の PowerShell で実行します。

```powershell
schtasks /Create /TN "TestStat Backend" /SC ONSTART /DELAY 0000:30 /TR '"c:\app\TestStat\teststat-server\run_server.bat"' /RL HIGHEST /RU "<実行ユーザー>" /RP "<パスワード>"
```

登録確認:

```powershell
schtasks /Query /TN "TestStat Backend" /V /FO LIST
```

手動起動:

```powershell
schtasks /Run /TN "TestStat Backend"
```

停止する場合はタスクスケジューラから `終了` を選択します。コマンドで停止する場合は以下です。

```powershell
schtasks /End /TN "TestStat Backend"
```

## 4. フロントエンドのビルドと IIS 配置

### 4.1 初回ビルド

`/tstat` 配下で公開する場合、Vite のビルド成果物と API 呼び出しが `/tstat` をベースにする必要があります。`teststat-frontend\.env` を以下のように設定してからビルドしてください。

```env
VITE_APP_BASE_PATH=/tstat/
VITE_API_BASE_PATH=/tstat
VITE_BACKEND_URL=http://localhost:18000
```

- `VITE_APP_BASE_PATH`: 画面・JS・CSS などの静的ファイルを `/tstat/` 配下で参照するための設定
- `VITE_API_BASE_PATH`: フロントエンドから `/tstat/api/*`、`/tstat/health` を呼ぶための設定
- `VITE_BACKEND_URL`: 開発サーバー起動時の proxy 先。IIS の本番配信では直接参照されません。

```powershell
cd c:\app\TestStat
.\rebuild_frontend.bat
```

`rebuild_frontend.bat` は以下を実行します。

1. `teststat-frontend` に移動
2. `npm run build` で `dist` を生成

エクスプローラから `rebuild_frontend.bat` を右クリックして `管理者として実行` しても動作します。管理者実行時は開始場所が変わることがあるため、bat は自身の配置場所を基準に `teststat-frontend` を探します。

### 4.2 IIS サイト設定

IIS マネージャーで設定します。

1. `Default Web Site` など公開対象の既存サイトを選択します。
2. 右クリックして `アプリケーションの追加...` を選択します。
3. アプリケーション情報を入力します。
   - エイリアス: `tstat`
   - 物理パス: `c:\app\TestStat\teststat-frontend\dist`
   - アプリケーションプール: 静的ファイル配信のみであれば既定のものでも構いません。
4. `http://<server-name>/tstat` で静的ファイルが表示できることを確認します。

フロントエンドは API を呼び出すため、IIS の URL Rewrite と ARR でバックエンドへ転送します。`/tstat` 配下に API もまとめる場合は、以下の転送を設定します。

- `/tstat/api/*` を `http://127.0.0.1:18000/api/*` にリバースプロキシ
- `/tstat/health` を `http://127.0.0.1:18000/health` にリバースプロキシ

`VITE_API_BASE_PATH=/tstat` でビルドすると、フロントエンドは `/tstat/api/*` と `/tstat/health` を呼び出します。別端末からアクセスした場合も IIS と同じオリジンになるため、バックエンドの 18000 ポートを直接公開したり CORS を設定したりする必要はありません。

`web.config` を `dist` 配下に置く運用にする場合、`npm run build` により `dist` が再生成されると `web.config` が削除される可能性があります。この bat ファイルでは `web.config` の作成や書き換えは行わないため、URL Rewrite 規則は IIS 側の運用手順として管理してください。

### 4.3 動作確認

ブラウザまたは PowerShell で確認します。

```powershell
curl http://localhost/tstat/health
```

ブラウザで以下を開きます。

```text
http://<server-name>/tstat
```

画面が表示され、API を使う操作が成功すればセットアップ完了です。

## 5. フロントエンド更新時の再ビルド

ソースを更新した後、PowerShell またはコマンドプロンプトで実行します。

```powershell
cd c:\app\TestStat
git pull
.\rebuild_frontend.bat
```

依存パッケージの追加・更新がある場合は、事前に以下を実行します。

```powershell
cd c:\app\TestStat\teststat-frontend
npm ci
```

IIS は静的ファイルを配信するだけなので、通常は IIS の再起動は不要です。ブラウザキャッシュが残る場合は、ブラウザをハードリロードしてください。

## 6. バックエンド更新時の反映

バックエンドの依存関係や DB スキーマに変更がある場合は、以下を実行します。

```powershell
cd c:\app\TestStat\teststat-server
git pull
.\.venv\Scripts\activate
pip install .
.\migrate_db.ps1
```

その後、タスクスケジューラで `TestStat Backend` を停止してから再実行します。

```powershell
schtasks /End /TN "TestStat Backend"
schtasks /Run /TN "TestStat Backend"
```

## 7. トラブルシュート

### 7.1 `http://localhost/tstat/health` が 502 になる

- バックエンドが起動しているか確認します。
- `http://127.0.0.1:18000/health` が直接成功するか確認します。
- ARR の `Enable proxy` が有効か確認します。

### 7.2 フロントエンドは表示されるが API が失敗する

- IIS の URL Rewrite 規則で `/tstat/api` と `/tstat/health` がバックエンドへ転送されているか確認します。
- `teststat-frontend\.env` の `VITE_API_BASE_PATH` が `/tstat` になっているか確認します。
- ブラウザの開発者ツールで失敗している URL とステータスコードを確認します。
- バックエンドの `.env` と DB 接続を確認します。

### 7.3 タスクスケジューラでは起動しない

- タスクの `開始` が `c:\app\TestStat\teststat-server` になっているか確認します。
- 実行アカウントが `.venv`、`.env`、PostgreSQL、必要な環境変数にアクセスできるか確認します。
- `ユーザーがログオンしているかどうかにかかわらず実行する` と `最上位の特権で実行する` を確認します。

### 7.4 `rebuild_frontend.bat` でビルドに失敗する

- Node.js と npm がインストールされているか確認します。
- `teststat-frontend\node_modules` 配下のファイルをエディタやウイルス対策ソフトがロックしていないか確認します。
- 必要に応じて管理者権限の PowerShell またはコマンドプロンプトから実行します。
