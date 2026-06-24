# TestStat-CLI

```
  _____         _   ____  _        _      ____ _     ___
 |_   _|__  ___| |_/ ___|| |_ __ _| |_   / ___| |   |_ _|
   | |/ _ \/ __| __\___ \| __/ _` | __| | |   | |    | |
   | |  __/\__ \ |_ ___) | || (_| | |_  | |___| |___ | |
   |_|\___||___/\__|____/ \__\__,_|\__|  \____|_____|___|
```

Excelテスト仕様書からテスト結果を集計するCLIツールです。

## 概要

このツールは、Excelファイル（.xlsx）に記録されたテスト結果を読み取り、以下の集計を行います：

- テストケース数の集計
- テスト結果別（Pass/Fail/Blocked...）の集計
- 日別・担当者別・環境別の集計
- 完了率・消化率の算出
- テーブル形式でのコンソール出力、CSV形式でのレポートなど様々な形式での出力

## インストール

### 前提条件

- Python 3.7以上
- SharePoint上のファイルをリストファイルで指定して集計する場合は、[Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) および `az login` でのログインが追加で必要です（詳細は「SharePoint連携機能」参照）。

### セットアップ

```bash
# ディレクトリに移動
cd teststat-cli

# パッケージとしてインストール
pip install .

# または、開発モードでインストール
pip install -e .
```

インストール後、`tstat`コマンドがグローバルに利用可能になります。

### アンインストール

```bash
pip uninstall teststat-cli
```

## 使い方

### 基本コマンド

```bash
tstat [オプション] [ファイルパス/フォルダパス]
```

### コマンドラインオプション

| オプション | 短縮形 | 説明 | デフォルト値 |
|------------|--------|------|--------------|
| `path` | - | 集計対象のファイルまたはフォルダのパス | 必須 |
| `-c, --config` | `-c` | 設定ファイルのパス | `config.json` |
| `-l, --list` | `-l` | プロジェクトリストファイルのパス（YAML形式） | なし |
| `-f, --output-format` | `-f` | 出力形式（table/json/csv） | `table` |
| `-o, --output-file` | `-o` | 出力ファイルパス | なし（コンソール出力のみ） |
| `-j, --json` | `-j` | JSON形式でサマリ出力 | `false` |
| `-J, --json-detailed` | `-J` | JSON形式で詳細出力 | `false` |
| `-v, --verbose` | `-v` | 詳細ログ出力（エラー発生時のトレース） | `false` |
| `-p, --clipboard` | `-p` | 集計データをTSV形式でクリップボードにコピー | `false` |
| `--detailed` | - | 複数ファイル処理時にファイル別の詳細結果も表示 | `false` |
| `-h, --help` | `-h` | ヘルプ表示 | - |

### Skillsファイルのインストール

AIエージェントからTestStat-CLIを実行しやすくするため、スラッシュコマンドとスキルをカレントディレクトリへ配置できます。

```bash
tstat --install-skills
```

配置されるファイル:

- `.claude/commands/tstat.md`
- `.agents/skills/teststat-cli/SKILL.md`

既存ファイルがある場合は上書きせずスキップします。上書きする場合は `--force` を指定します。

```bash
tstat --install-skills --force
```

生成されるAIエージェント用ファイルでは、エージェントが解析しやすいように `tstat --json ...` を使う指示を含めています。

### オプション使用例
```bash
# 単一ファイルの集計
tstat path/to/your_file.xlsx

# 複数ファイルの集計（複数のxlsxファイルを直接指定）
tstat path/to/file1.xlsx path/to/file2.xlsx path/to/file3.xlsx

# フォルダ内の全Excelファイルを集計
tstat path/to/your_folder

# プロジェクトリストファイル使用（YAML形式）
tstat -l project_list.yaml

# カスタム設定ファイルを使用
tstat path/to/your_file.xlsx -c custom_config.json

# JSON形式でサマリ出力
tstat path/to/your_file.xlsx -j

# JSON形式で詳細出力
tstat path/to/your_file.xlsx -J

# CSV形式でファイル出力
tstat path/to/your_file.xlsx -o results.csv

# 詳細ログ出力
tstat path/to/your_file.xlsx -v

# TSV形式でクリップボードにコピー
tstat path/to/your_file.xlsx -p

# 詳細出力オプション（複数ファイル処理時）
tstat --detailed path/to/file1.xlsx path/to/file2.xlsx
```

## 出力形式

### テーブル形式出力（デフォルト）

複数ファイルを読み取った場合のサマリー表示例です。

```
SUMMARY RESULTS
────────────────

Project: サンプルプロジェクト
Processed Files: 3
Execution Time: 2024-04-29 10:00:00

TOTAL RESULTS
─────────────
┌───────┬──────┬───────┬──────┬─────────┬─────────┬─────┬────────┬──────────────┬─────────────┐
│ Total │ Pass │ Fixed │ Fail │ Blocked │ Suspend │ N/A │ 未実施 │ 完了数       │ 消化数      │
├───────┼──────┼───────┼──────┼─────────┼─────────┼─────┼────────┼──────────────┼─────────────┤
│ 112   │ 55   │ 2     │ 1    │ 1       │ 0       │ 9   │ 44     │ 66 (58.93%)  │ 68 (60.71%) │
└───────┴──────┴───────┴──────┴─────────┴─────────┴─────┴────────┴──────────────┴─────────────┘

FILE BREAKDOWN
──────────────
┌─────────┬───────┬───────┬──────┬───────┬──────┬─────────┬─────────┬─────┬────────┐
│ File    │ Env   │ Total │ Pass │ Fixed │ Fail │ Blocked │ Suspend │ N/A │ 未実施 │
├─────────┼───────┼───────┼──────┼───────┼──────┼─────────┼─────────┼─────┼────────┤
│ TEST001 │ 環境A │ 24    │ 15   │ 1     │ 1    │ 1       │ 0       │ 0   │ 6      │
│ TEST001 │ 環境B │ 12    │ 7    │ 0     │ 0    │ 0       │ 0       │ 0   │ 5      │
│ TEST002 │ -     │ 76    │ 33   │ 1     │ 0    │ 0       │ 0       │ 9   │ 33     │
└─────────┴───────┴───────┴──────┴───────┴──────┴─────────┴─────────┴─────┴────────┘

PROGRESS SUMMARY
────────────────
┌─────────┬───────┬───────┬──────────────┬─────────────┬────────────┬───────────────┐
│ File    │ Env   │ Total │ Completed    │ Executed    │ Start Date │ Latest Update │
├─────────┼───────┼───────┼──────────────┼─────────────┼────────────┼───────────────┤
│ TEST001 │ 環境A │ 24    │ 16 (66.67%)  │ 18 (75.0%)  │ 2024-02-09 │ 2024-02-15    │
│ TEST001 │ 環境B │ 12    │ 7 (58.33%)   │ 7 (58.33%)  │ 2024-02-11 │ 2024-02-12    │
│ TEST002 │ -     │ 76    │ 43 (56.58%)  │ 43 (56.58%) │ 2024-01-29 │ 2024-03-09    │
├─────────┼───────┼───────┼──────────────┼─────────────┼────────────┼───────────────┤
│ Total   │ -     │ 112   │ 66 (58.93%)  │ 68 (60.71%) │ 2024-01-29 │ 2024-03-09    │
└─────────┴───────┴───────┴──────────────┴─────────────┴────────────┴───────────────┘
```

対応ターミナルでは、見出し、テーブルヘッダ、ステータス、警告、主要な結果列に色が付きます。色を無効にしたい場合は `NO_COLOR` 環境変数を設定してください。

### サマリJSON形式出力（`--json` オプション）

通常のコンソール出力に近い粒度で、`SUMMARY RESULTS`、`TOTAL RESULTS`、単一ファイルの場合は `DAILY BREAKDOWN`、複数ファイルの場合は `FILE BREAKDOWN` 相当の情報のみを出力します。

単一ファイルを処理した場合のJSON出力例です。

```json
{
  "summary_results": {
    "file": "input_sample/sample1.xlsx",
    "total_cases": 36,
    "available_cases": 36,
    "excluded_cases": 0,
    "status": "進行中",
    "start_date": "2025-02-09",
    "last_update": "2025-02-15"
  },
  "total_results": {
    "Total": 36,
    "Pass": 32,
    "Fixed": 1,
    "Fail": 1,
    "Blocked": 1,
    "Suspend": 0,
    "N/A": 0,
    "未実施": 1,
    "完了数": 33,
    "消化数": 35,
    "完了率(%)": 91.67,
    "消化率(%)": 97.22
  },
  "daily_breakdown": {
    "2025-02-09": {
      "Pass": 1,
      "Fixed": 0,
      "Fail": 0,
      "Blocked": 0,
      "Suspend": 0,
      "N/A": 0,
      "完了数": 1,
      "消化数": 1
    }
  }
}
```

### 詳細JSON形式出力（`-J, --json-detailed` オプション）

複数ファイルを処理した場合のJSON出力例です。

```json
{
  "summary": {
    "processed_files": 3,
    "total_stats": {
      "all": 112,
      "available": 112,
      "executed": 68,
      "completed": 66,
      "incompleted": 46,
      "planned": 112
    },
    "overall_status": "",
    "earliest_start_date": "2024-01-29",
    "latest_update": "2024-03-09",
    "total_results": {
      "Pass": 55,
      "Fixed": 2,
      "Fail": 1,
      "Blocked": 1,
      "Suspend": 0,
      "N/A": 9,
      "未実施": 44,
      "Total": 112,
      "完了数": 66,
      "消化数": 68,
      "完了率(%)": 58.93,
      "消化率(%)": 60.71
    }
  },
  "files": [
    {
      "file": "input_sample/sample1.xlsx",
      "stats": { "all": 24, "available": 24, ... },
      "total": { "Pass": 15, "Fixed": 1, ... },
      "run": { "status": "完了", "start_date": "2024-02-09", ... },
      "label": "TEST001"
    },
    {
      "file": "input_sample/sample2.xlsx",
      "stats": { "all": 76, "available": 76, ... },
      "total": { "Pass": 33, "Fixed": 1, ... },
      "run": { "status": "進行中", "start_date": "2024-01-29", ... },
      "label": "TEST002"
    }
  ]
}
```

### 複数ファイル処理

複数のxlsxファイルを同時に処理する場合、以下の方法があります：

#### 1. 直接指定による複数ファイル処理
```bash
# 複数のxlsxファイルを直接指定
tstat.exe file1.xlsx file2.xlsx file3.xlsx

# パスに空白が含まれる場合は引用符で囲む
tstat.exe "D:\Script\TestStat-CLI\input_sample\sample1.xlsx" "D:\Script\TestStat-CLI\input_sample\sample2_abcdegfg.xlsx"
```

# YAML形式のプロジェクトリストファイルを使用
tstat.exe -l project_list.yaml

#### 複数ファイル処理の出力内容
複数ファイルを処理した場合、以下の情報が表示されます：

- **TOTAL RESULTS**: 全ファイルの統合集計結果
- **FILE BREAKDOWN**: 各ファイルの個別サマリー
- **ERROR SUMMARY**: エラーが発生したファイルの一覧
- **OVERALL STATUS**: 全体のステータス情報
- **各ファイルの詳細**: 各ファイルの個別詳細集計（`--detailed`オプション指定時のみ）

**デフォルト動作**: 複数ファイル処理時は、サマリー情報のみが表示され、各ファイルの詳細な結果（日別集計、担当者別集計、環境別集計など）は表示されません。

**詳細出力**: `--detailed`オプションを指定すると、各ファイルの詳細な結果も表示されます。

### CSV形式出力（`-f, --output-format` オプションで `csv` を指定）

CSV形式でファイルに出力する場合、以下のような構造でデータが出力されます：

**単一ファイル処理の場合**:
- TOTAL RESULTS: 集計結果のサマリー
- STATISTICS: 統計情報
- DAILY BREAKDOWN: 日別集計
- BY NAME: 担当者別集計
- BY ENVIRONMENT: 環境別集計

**複数ファイル処理の場合**:
- TOTAL RESULTS: 統合集計結果
- SUMMARY STATISTICS: 統合統計情報
- INDIVIDUAL FILES: 各ファイルのサマリー


## 設定ファイル仕様

### config.json

デフォルトで `config.json` の設定を使用します。
`config.json` が存在しない場合は、同梱の `assets/default_config.json` を複製して自動作成します。
`-c, --config` で任意のファイルを読み込むこともできます。

独自の `config.json` を用意する際は、リポジトリの `config_sample.json` を参考にしてください。
全設定項目とその用途がひとつのファイルにまとまっています。

```bash
# config_sample.json をコピーして編集する
cp config_sample.json config.json
```

```json
{
  "read_definition": {
    "target_sheets": ["テスト項目"],
    "ignore_sheets": [],
    "include_hidden_sheets": false,
    "header": {"search_col": "A", "search_key": "#"},
    "tobe_row": {"keys": ["期待", "実施対象"]},
    "result_row": {"keys": ["結果"], "ignores": ["期待結果"]},
    "person_row": {"keys": ["担当者"]},
    "date_row": {"keys": ["日付", "実施日"]},
    "plan_row": {"keys": ["計画"]},
    "excluded": ["対象外"]
  },
  "test_status": {
    "results": ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"],
    "completed_results": ["Pass", "Fixed", "Suspend", "N/A"],
    "executed_results": ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"],
    "labels": {
      "completed": "完了数",
      "executed": "消化数",
      "planned": "計画数",
      "not_run": "未着手"
    }
  },
  "output_definition": {
    "state": {
      "completed": {"name": "完了", "foreground": "darkgreen", "background": "darkseagreen1"},
      "in_progress": {"name": "進行中", "foreground": "dodgerblue4", "background": "skyblue"},
      "not_started": {"name": "未着手", "foreground": "dimgray", "background": "silver"}
    }
  }
}
```

### lists/*.yaml

`-l, --list` で読み込む YAML には、処理対象の Excel ファイルと、ファイルごとの読み取り設定を指定できます。
ファイルごとの設定は `config.json` の `read_definition` より優先されます。

最上段の `project:` ラッパーは**省略可能**で、トップレベルに直接 `project_name` / `files` などを記述できます。
後方互換のため、`project:` 配下にネストする旧形式も引き続き読み込めます。

```yaml
# project: ラッパーを省略した記法（推奨）
project_name: サンプルプロジェクト
testing_id: 1001
subtask_id: 999
base_dir: input_sample
files:
  - label: TEST001
    path: sample1.xlsx
    subtask_id: 123
    target_sheets:
      - テスト項目
    ignore_sheets:
      - Sheet1
    include_hidden_sheets: false
    target_environments:
      - 環境a
    ignore_environments:
      - 環境b

  - label: TEST002
    path: sample2.xlsx
```

```yaml
# project: ラッパーを使う旧形式（後方互換）
project:
  project_name: サンプルプロジェクト
  base_dir: input_sample
  files:
    - label: TEST001
      path: sample1.xlsx
```

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `project_name` | 必須 | プロジェクト名。サマリー表示やJSON出力のプロジェクト名に使用されます。 |
| `files` | 必須 | 処理対象のファイル定義リスト。1件以上指定します。 |
| `testing_id` | 任意 | TestStatバックエンドへの進捗データ送信で使用するテスト識別ID。整数で指定します。 |
| `subtask_id` | 任意 | プロジェクト全体のAPI連携で更新対象にするサブタスクID。全ファイルの合計進捗率と最も古い開始日を送信します。 |
| `base_dir` | 任意 | ローカルの相対 `files[].path` を解決する共通ディレクトリ。絶対パスと SharePoint URL には適用されません。 |

> 旧形式を使う場合は、上記項目を `project:` 配下にネストして記述します（例: `project.project_name`）。

`base_dir` を指定すると、`files[].path` に `sample1.xlsx` や `sub/sample2.xlsx` のようなファイル名・相対パスだけを書けます。`files[].path` に `C:/...` などの絶対パスを指定した場合は、その値が優先されます。

`project.files` の各要素では、以下の項目を指定できます。

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `label` | 必須 | ファイルを識別する任意のラベル。出力時の表示名として使用されます。 |
| `path` | 必須 | 処理対象の `.xlsx` ファイル、または `.xlsx` を含むディレクトリのパス。`http://` / `https://` で始まる SharePoint の共有 URL も指定でき、実行時に一時フォルダへダウンロードして集計します（後述「SharePoint連携機能」参照）。 |
| `subtask_id` | 任意 | API連携で更新対象にするサブタスクID。未指定の場合、そのファイルのAPI連携はスキップされます。 |
| `target_sheets` | 任意 | 集計対象シート名を検索するキーワードリスト。指定すると `config.json` の `read_definition.target_sheets` を上書きします。空リストの場合は全シートが対象です。 |
| `ignore_sheets` | 任意 | 集計対象から除外するシート名キーワードリスト。`target_sheets` に一致しても、このキーワードを含むシートは除外されます。 |
| `include_hidden_sheets` | 任意 | `true` の場合、Excelで非表示に設定されたシートも集計対象に含めます。未指定時は `config.json` の設定を使用します。 |
| `target_environments` | 任意 | 集計対象にする環境名キーワードリスト。結果列セット名にいずれかのキーワードを含む環境だけを集計します。 |
| `ignore_environments` | 任意 | 集計対象から除外する環境名キーワードリスト。結果列セット名にいずれかのキーワードを含む環境は除外されます。 |

`target_sheets` / `ignore_sheets` / `target_environments` / `ignore_environments` は部分一致で判定されます。

### 設定項目の説明

#### read_definition
- `target_sheets`: 対象シートを検索するキーワード
- `ignore_sheets`: 除外するシートを検索するキーワード
- `include_hidden_sheets`: Excelで非表示に設定されたシートを集計対象に含めるかどうか
- `header`: ヘッダー行の検索設定
- `result_row`: 結果列の検索設定
- `person_row`: 担当者列の検索設定
- `date_row`: 日付列の検索設定
- `plan_row`: 計画列の検索設定
- `excluded`: 除外対象のキーワード

#### test_status
- `results`: 結果タイプの名称および順序
- `completed_results`: 完了数のカウントに含める結果タイプ
- `executed_results`: 消化数のカウントに含める結果タイプ
- `labels`: 各指標の表示ラベル

#### output_definition
- `state`: ステータス表示の設定

#### wbs_api
- `enabled`: API連携機能の有効/無効
- `base_url`: 連携先APIのベースURL

## API連携機能

集計したテスト進捗率を外部のWBS管理ツールなどのAPIへ自動的に送信する機能です。
この機能を使用すると、Excelを更新して本ツールを実行するだけで、管理ツールの進捗率も同期させることができます。

### 設定方法

#### 1. config.json の設定

**TestStatサーバーへの進捗データ送信（`reporting_api`）**

`config.json` の `reporting_api` セクションで、TestStatサーバーの接続情報を設定します。

```json
{
  "reporting_api": {
    "enabled": true,
    "send": true,
    "base_url": "http://your-teststat-server:18000/api",
    "sender": null
  }
}
```

- `enabled`: `false` にすると TestStat サーバー連携全体（進捗データ送信に加え、`-t/--testing-id` によるリストのダウンロードも）を無効にします（デフォルトは `true`）。
- `send`: `false` にすると進捗データの送信のみをスキップします（デフォルトは `true`）。`enabled: true` のままにしておけば、`-t/--testing-id` によるリストのダウンロードや集計は実行しつつ、送信だけを止められます。
- `base_url`: TestStatサーバーのベースURLを末尾の `/api` まで含めて指定します。`-l, --list` でYAMLを指定した際に `project.testing_id` が設定されていると、`{base_url}/v1/progress` へ集計結果を送信します。`http://<server-name>/tstat/api` のように指定します。
- `sender`: 送信者名を文字列で指定します（任意）。`null` の場合は送信者情報を含みません。

**WBS管理ツールへの進捗率送信（`wbs_api`）**

`config.json` の `wbs_api` セクションで、接続情報を設定します。

```json
{
  "wbs_api": {
    "enabled": true,
    "base_url": "http://your-wbs-tool.com/api"
  }
}
```

- `enabled`: `true` に設定するとAPI連携が有効になります（デフォルトは `false`）。
- `base_url`: WBS管理ツールのベースURLを末尾の `/api` まで含めて指定します。

#### 2. プロジェクトリスト（YAML）の設定

API連携を行う対象に `subtask_id` を指定します。
プロジェクト全体の結果を連携する場合は `project.subtask_id`、ファイルごとの結果を連携する場合は `files[].subtask_id` を使用します。

```yaml
project:
  project_name: サンプルプロジェクト
  testing_id: 1001  # TestStatバックエンドへ送信するテスト識別ID
  subtask_id: 999  # プロジェクト全体の更新対象サブタスクID
  files:
    - label: TEST001
      path: input_sample/sample1.xlsx
      subtask_id: 123  # ファイル単位の更新対象サブタスクID
```

`project.testing_id` は、TestStatバックエンドに送信する進捗データを識別するためのIDです。
`-l, --list` でYAMLを指定して実行した場合、`project.testing_id` が設定されていると集計結果を `{reporting_api.base_url}/v1/progress` へ送信します。
`testing_id` は整数で指定してください。未設定の場合、通常の集計処理は継続されますが、TestStatバックエンドへの進捗データ送信はスキップされ、警告が表示されます。

`project.subtask_id` が設定されている場合は、全ファイルの合計の `完了数 / 実施対象数` から進捗率を算出し、全ファイルで最も古い実施日を `actual_start_date` として送信します。
同じ `subtask_id` が `project.subtask_id` と `files[].subtask_id` の両方に指定されている場合、そのIDへの送信はプロジェクト全体の結果を優先し、ファイル単位の送信は行いません。
`subtask_id` が設定されていないファイルについては、ファイル単位のAPI連携はスキップされます。

### API仕様

本ツールは集計完了後、指定された `subtask_id` ごとに以下のリクエストを送信します。

- **HTTPメソッド**: `PATCH`
- **URL**: `{base_url}/subtasks/{subtask_id}`
- **Content-Type**: `application/json`
- **リクエストボディ**:

```json
{
  "progress_percent": 85,
  "actual_start_date": "2024-02-09"
}
```

- `progress_percent`: 完了数 / 実施対象数 × 100 で算出された整数値。
- `actual_start_date`: Excelから取得された最も古い実施日（存在する場合のみ送信）。

## SharePoint連携機能

リストファイル（YAML）の `files[].path` に SharePoint の共有 URL を指定すると、
実行時に Microsoft Graph API 経由でファイルを一時フォルダへダウンロードして集計します。
集計が完了すると一時ファイルは自動的に削除されるため、ローカルにファイルを置く必要がありません。

### 前提条件

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) がインストールされていること
- `az login` でログイン済みであること（アクセストークンの取得に使用します）
- ログインアカウントに対象ファイルへの読み取り権限があること

実行環境によっては、コマンドプロンプトでは `az` が使えても `tstat` から Azure CLI を見つけられない場合があります。
その場合は Azure CLI の実体パスを環境変数 `TESTSTAT_AZ_CLI_PATH` に指定してください。

```cmd
set TESTSTAT_AZ_CLI_PATH=C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd
```

### 使い方

「リンクのコピー」で取得した共有 URL を `path` に指定します。

```yaml
project:
  project_name: サンプルプロジェクト
  testing_id: 1001
  files:
    - label: シナリオテスト
      path: "https://contoso.sharepoint.com/:x:/s/yoursite/EabcdEFGH123..."  # SharePoint共有URL
      target_sheets:
        - テスト項目
    - label: 性能テスト
      path: input_sample/sample2.xlsx   # 従来どおりローカルパスも併用可
```

```bash
# 事前に Azure CLI でログイン
az login

# リストファイルを指定して実行（URLのファイルは自動ダウンロード）
tstat -l project_list.yaml
```

### config.json の設定

`sharepoint` セクションで動作を制御できます（省略時は下記がデフォルト）。

```json
{
  "sharepoint": {
    "enabled": true,
    "auth_method": "az_cli",
    "graph_endpoint": "https://graph.microsoft.com/v1.0",
    "timeout_sec": 60,
    "temp_dir": null,
    "cleanup": true
  }
}
```

- `enabled`: `false` にすると URL 指定のファイルはスキップされます。
- `graph_endpoint`: Microsoft Graph のエンドポイント。
- `timeout_sec`: Graph API 呼び出し・ダウンロードのタイムアウト秒数。
- `temp_dir`: ダウンロード先の一時フォルダ。`null` の場合は OS の一時フォルダを使用します。
- `cleanup`: `false` にすると一時ファイルを削除せず残します（デバッグ用）。

### 注意事項

- 問題の切り分け時は `-v` / `--verbose` を付けて実行してください。Azure CLI の検出結果、
  `az account get-access-token` の終了コード、Graph API のステータス、ダウンロード先の一時パスなどを表示します。
  アクセストークンと署名付きダウンロード URL はログに出力しません。
- 共有 URL は「リンクのコピー」で得られる URL（`:x:/s/...` 形式）を使用してください。
  Excel の「発行」や埋め込みで得られる `_layouts/15/Doc.aspx?sourcedoc={GUID}...` 形式の URL は解決できないことがあります。
- `403` エラーが発生する場合、`az login` のトークンに `Files.Read.All` / `Sites.Read.All` 相当の
  スコープが付与されていない可能性があります。適切なスコープを持つアカウントでのログイン、
  または管理者同意が必要です。
- 位置引数での URL 直接指定（`tstat https://...`）には対応していません。リストファイル経由で指定してください。

## Excelファイル形式

### 対応形式
- ファイル形式: .xlsx
- エンコーディング: UTF-8

### シート構造
1. **ヘッダー行**: `#` で始まる行をヘッダーとして認識
2. **データ行**: ヘッダー行以降の行をデータとして処理
3. **列構成**:
   - 結果列: テスト結果（Pass/Fail/Blocked等）
   - 担当者列: テスト担当者名
   - 日付列: テスト実施日
   - 計画列: テスト計画日（オプション）

### サンプルデータ
```
# テスト項目    結果    担当者    日付      計画
テストケース1   Pass    テスト太郎     2024-01-15 2024-01-10
テストケース2   Fail    テスト次郎     2024-01-16 2024-01-10
テストケース3   Blocked テスト三郎     2024-01-17 2024-01-10
```

## エラーハンドリング

### 主なエラーケース

1. **ファイル未検出**
   ```
   ERROR: 指定されたパスが存在しません: /path/to/file.xlsx
   ```

2. **設定ファイル不正**
   ```
   ERROR: 設定ファイルのJSON形式が不正です: config.json
   詳細: Expecting ',' delimiter: line 10 column 5
   ```

3. **Excelファイル形式エラー**
   ```
   ERROR: ファイル処理中にエラーが発生しました: sample.xlsx
   詳細: [Errno 13] Permission denied
   ```

4. **データ読み取りエラー**
   ```
   ERROR: シートが見つかりませんでした。
   ```

### エラー対処法

- **ファイルが見つからない**: パスを確認し、ファイルが存在することを確認
- **権限エラー**: ファイルの読み取り権限を確認
- **設定ファイルエラー**: JSON形式の構文を確認
- **シートが見つからない**: Excelファイル内に「テスト項目」を含むシートが存在することを確認

## 開発・カスタマイズ

### プロジェクト構造
```
teststat-cli/
├── test_stat_cli.py       # メインCLI
├── pyproject.toml         # プロジェクト設定
├── setup.py               # インストールスクリプト
├── requirements.txt       # 依存関係
├── lists/                 # プロジェクトリスト
│   └── list_sample.yaml   # YAMLサンプル
├── utils/                 # ユーティリティ（主要モジュール）
│   ├── ExcelProcessor.py  # Excel解析
│   ├── DataAggregator.py  # データ集計
│   ├── ApiIntegration.py  # API連携
│   ├── OutputWriter.py    # 出力処理
│   ├── ReadData.py        # データ読み取り
│   └── Utility.py         # 共通ユーティリティ
└── assets/                # アセット
    ├── default_config.json # デフォルト設定ファイル
    └── logo.txt           # ロゴ
```

### 拡張ポイント
- `utils/ReadData.py`: データ読み取りロジックのカスタマイズ
- `config.json`: ローカル環境用の設定による動作のカスタマイズ
- `test_stat_cli.py`: 出力形式のカスタマイズ

## ライセンス

MIT
