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

### セットアップ

```bash
# リポジトリのクローン
git clone <repository-url>
cd TestStat-CLI

# パッケージとしてインストール
pip install .

# または、開発モードでインストール
pip install -e .
```

インストール後、`tstat`コマンドがグローバルに利用可能になります。

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
| `-j, --json-output` | `-j` | JSON形式で出力 | `false` |
| `-v, --verbose` | `-v` | 詳細ログ出力（エラー発生時のトレース） | `false` |
| `-p, --clipboard` | `-p` | 集計データをTSV形式でクリップボードにコピー | `false` |
| `--detailed` | - | 複数ファイル処理時にファイル別の詳細結果も表示 | `false` |
| `-h, --help` | `-h` | ヘルプ表示 | - |

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

# JSON形式で出力
tstat path/to/your_file.xlsx -j

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

```
==================================================
Summary Results
==================================================

File: path/to/your_file.xlsx
Total Cases: 150
Available Cases: 145
Excluded Cases: 5

TOTAL RESULTS:
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────────┬─────────────┐
│ Pass    │ Fixed   │ Fail    │ Blocked │ Suspend │ N/A     │ Total   │ 完了数   │ 消化数   │ 完了率(%)   │ 消化率(%)   │
├─────────┼─────────┼─────────┼─────────┼─────────┼─────────┼─────────┼─────────┼─────────┼─────────────┼─────────────┤
│ 120     │ 5       │ 10      │ 3       │ 2       │ 0       │ 140     │ 127     │ 140     │ 87.59       │ 96.55       │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────────┴─────────────┘

STATISTICS:
┌─────────────┬─────────┐
│ Metric      │ Count   │
├─────────────┼─────────┤
│ All         │ 150     │
│ Available   │ 145     │
│ Executed    │ 140     │
│ Completed   │ 127     │
│ Incompleted │ 13      │
│ Planned     │ 150     │
└─────────────┴─────────┘

STATUS: 進行中
Start Date: 2024-01-15
Last Update: 2024-01-20
```

### JSON形式出力（`-j, --json-output` オプション）

```json
{
  "file": "path/to/your_file.xlsx",
  "stats": {
    "all": 150,
    "available": 145,
    "excluded": 5,
    "executed": 140,
    "completed": 127,
    "incompleted": 13,
    "planned": 150
  },
  "total": {
    "Pass": 120,
    "Fixed": 5,
    "Fail": 10,
    "Blocked": 3,
    "Suspend": 2,
    "N/A": 0,
    "Total": 140,
    "完了数": 127,
    "消化数": 140,
    "完了率(%)": 87.59,
    "消化率(%)": 96.55
  },
  "run": {
    "status": "進行中",
    "start_date": "2024-01-15",
    "last_update": "2024-01-20"
  }
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
`-c, --config` で任意のファイルを読み込むこともできます。

```json
{
  "read_definition": {
    "target_sheets": ["テスト項目"],
    "ignore_sheets": [],
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

### 設定項目の説明

#### read_definition
- `target_sheets`: 対象シートを検索するキーワード
- `ignore_sheets`: 除外するシートを検索するキーワード
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
TestStatCLI/
├── test_stat_cli.py       # メインCLI
├── config.json            # 設定ファイル
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
    └── logo.txt           # ロゴ
```

### 拡張ポイント
- `utils/ReadData.py`: データ読み取りロジックのカスタマイズ
- `config.json`: 設定による動作のカスタマイズ
- `test_stat_cli.py`: 出力形式のカスタマイズ

## ライセンス

MIT
