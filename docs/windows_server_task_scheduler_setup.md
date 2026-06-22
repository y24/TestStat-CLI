# Windows Server タスクスケジューラによる識別子 URL 自動収集

対象: `teststat-server/collect.bat`


## Windows Server 事前セットアップ

この機能は `teststat-server` が DB から SharePoint URL 付き識別子を読み出し、`teststat-cli` の `tstat -l <自動生成YAML>` を起動して集計する。Windows Server では、以下を先に準備する。

### 1. リポジトリ配置と Python 環境

- `D:\Script\TestStat-CLI` など、タスク実行アカウントから読める固定パスにリポジトリを配置する。
- `teststat-server` の Python 環境を作成し、既存の server が起動できる状態にする。
- `teststat-cli` の Python 環境を作成し、`tstat` を実行できる状態にする。

例:

```cmd
cd /d D:\Script\TestStat-CLI\teststat-cli
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\tstat.exe --help
```

`teststat-cli` はインストールすると `tstat` console script を作成する。タスク実行アカウントや server プロセスから PATH 経由で `tstat` が見えるなら `TSTAT_COMMAND=tstat` でよい。

```cmd
where tstat
tstat --help
```

CLI を専用 venv にだけ入れている場合、その venv の `Scripts` は通常 PATH に出ない。`where tstat` が通らない場合は、CLI 側 venv の `tstat.exe` をフルパスで指定する。

### 2. tstat 設定ファイル

`teststat-cli/config.json` を用意し、少なくとも以下を確認する。

- `reporting_api.enabled` が `true` であること。
- `reporting_api.base_url` が TestStat Server を指していること。
  - 例: `http://localhost:18000`
  - IIS 配下で公開している場合は実際の公開 URL に合わせる。
- SharePoint URL を使う場合、`sharepoint.enabled` が `true` であること。

`TSTAT_CONFIG` にこの `config.json` のフルパスを設定すると、タスク実行時のカレントディレクトリに依存しない。

### 3. Azure CLI と az login

SharePoint ファイルの取得には Azure CLI が必要。Windows Server に Azure CLI をインストールし、収集を実行する Windows ユーザーで `az login` しておく。

```cmd
az --version
az login
az account get-access-token --resource https://graph.microsoft.com --query accessToken -o tsv
```

重要: `az login` のトークンは Windows ユーザーごとの `%USERPROFILE%\.azure` に保存される。どのユーザーでログインするかは実行方式で変わる。

- 直接呼び: タスクスケジューラで `collect.bat` を実行するアカウントが `az login` 済みであること。
- API 起動: `collect.bat api` は server に依頼するだけなので、server を起動しているアカウントが `az login` 済みであること。

タスクスケジューラを「ログオン状態に関わらず実行」にする場合も、同じ実行アカウントで事前に `az login` を済ませる。別アカウントでログインしてもトークンは共有されない。

Azure CLI が PATH から見つからない環境では、システム環境変数またはタスク実行アカウントの環境変数に `TESTSTAT_AZ_CLI_PATH` を設定する。

```cmd
setx TESTSTAT_AZ_CLI_PATH "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
```

### 4. SharePoint 権限

`az login` したアカウントには、登録する SharePoint 共有 URL のファイルを読む権限が必要。403 が出る場合は以下を確認する。

- 共有 URL が Excel ファイル単体の「リンクのコピー」で取得した URL であること。
- ログインアカウントがそのファイルをブラウザで開けること。
- 組織の条件付きアクセス、MFA、Graph スコープ、管理者同意の制約に引っかかっていないこと。

### 5. DB マイグレーションと server 再起動

この機能では `plan_labels.source_url` を使うため、server 側で Alembic を適用する。

```cmd
cd /d D:\Script\TestStat-CLI\teststat-server
.venv\Scripts\alembic.exe upgrade head
```

コード変更とマイグレーション適用後は、手動で backend を再起動する。現在の運用では `--reload` を使っていないため、再起動しないと変更は反映されない。

### 6. 動作確認

タスク登録前に、手動で以下を確認する。

```cmd
cd /d D:\Script\TestStat-CLI\teststat-server
collect.bat
```

API 起動方式を使う場合:

```cmd
cd /d D:\Script\TestStat-CLI\teststat-server
collect.bat api
```

最後に状態 API とログを確認する。

```http
GET http://localhost:18000/api/v1/collect/status
```

`auth_error: true` の場合は、まず実行ユーザーと `az login` 済みユーザーが一致しているかを確認する。

## 前提

- `plan_labels.source_url` 追加マイグレーションを適用済みであること。
- `teststat-server/.env` に `TSTAT_COMMAND` を設定していること。
- SharePoint 実接続では、収集を実行する Windows ユーザーで `az login` 済みであること。
- バックエンドのコード変更後は手動で server を再起動すること。

設定例:

```env
COLLECT_ENABLED=true
TSTAT_COMMAND=tstat
TSTAT_CONFIG=D:\Script\TestStat-CLI\teststat-cli\config.json
COLLECT_LOG_DIR=D:\Script\TestStat-CLI\teststat-server\logs
COLLECT_TIMEOUT_SEC=600
```

`tstat` 側の `config.json` は `reporting_api.base_url` が起動中の TestStat Server を指すように設定する。

`TSTAT_COMMAND=tstat` で失敗する場合は、実行アカウントの PATH から `tstat` が見えていない。`where tstat` で確認し、見つからない場合は CLI 側 venv の console script をフルパス指定する。

```env
TSTAT_COMMAND=D:\Script\TestStat-CLI\teststat-cli\.venv\Scripts\tstat.exe
```

## 実行方式

### 直接呼び

`collect.bat` をそのまま実行する。タスクスケジューラの実行アカウントが `az login` 済みである必要がある。

```bat
D:\Script\TestStat-CLI\teststat-server\collect.bat
```

終了コード:

- `0`: 成功、または対象なし
- `1`: 全対象失敗
- `2`: 認証系エラーを検知

### API 起動

起動中の server に収集を依頼する。`az login` が必要なのは server を起動しているアカウント。

```bat
D:\Script\TestStat-CLI\teststat-server\collect.bat api
```

## 登録例

毎時実行:

```cmd
schtasks /Create /TN "TestStat\CollectLabels" /TR "D:\Script\TestStat-CLI\teststat-server\collect.bat" /SC HOURLY /RU <実行アカウント> /RP * /RL HIGHEST /F
```

タスク設定では「既に実行中の場合、新しいインスタンスを開始しない」を選ぶ。API 側にも多重実行ガードがある。

## 状態確認

最後の実行結果は以下で確認できる。

```http
GET http://localhost:18000/api/v1/collect/status
```

`auth_error: true` の場合は `az login` の期限切れ、権限不足、401/403 などを疑う。ログは `COLLECT_LOG_DIR` の `collect_YYYYMMDD.log` に出力される。



