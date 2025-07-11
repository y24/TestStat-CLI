# TestSpecAnalytics CLI

```
  _____         _     ____
 |_   _|__  ___| |_  / ___| _ __   ___  ___
   | |/ _ \/ __| __| \___ \| '_ \ / _ \/ __|
   | |  __/\__ \ |_   ___) | |_) |  __/ (__
   |_|\___||___/\__| |____/| .__/ \___|\___|    ____ _     ___
    / \   _ __   __ _| |_  |_| |_(_) ___ ___   / ___| |   |_ _|
   / _ \ | '_ \ / _` | | | | | __| |/ __/ __| | |   | |    | |
  / ___ \| | | | (_| | | |_| | |_| | (__\__ \ | |___| |___ | |
 /_/   \_\_| |_|\__,_|_|\__, |\__|_|\___|___/  \____|_____|___|
                        |___/
```

Excelテスト仕様書からテスト結果を集計・分析するCLIツールです。

## 概要

このツールは、Excelファイル（.xlsx）に記録されたテスト結果を読み取り、以下の集計・分析を行います：

- テストケース数の統計
- 結果別（Pass/Fail/Blocked等）の集計
- 日別・担当者別・環境別の集計
- 完了率・消化率の算出
- 美しいテーブル形式での出力

## インストール

### 前提条件

- Python 3.7以上

### セットアップ

```bash
# リポジトリのクローン
git clone <repository-url>
cd TestSpecAnalyticsCLI

# 依存パッケージのインストール
pip install -r requirements.txt
```

## 使い方

### 基本的な使い方

```bash
# 単一ファイルの集計
python test_spec_analytics.py input_sample/sample1.xlsx

# フォルダ内の全Excelファイルを集計
python test_spec_analytics.py input_sample/

# プロジェクトリストファイル使用（JSON形式）
python test_spec_analytics.py -l project_list.json

# プロジェクトリストファイル使用（YAML形式）
python test_spec_analytics.py -l project_list.yaml

# プロジェクトリストファイル使用（テキスト形式）
python test_spec_analytics.py -l list_sample.txt

# カスタム設定ファイルを使用
python test_spec_analytics.py input_sample/sample1.xlsx -c custom_config.json

# JSON形式で出力
python test_spec_analytics.py input_sample/sample1.xlsx -j

# CSV形式でファイル出力
python test_spec_analytics.py input_sample/sample1.xlsx -o results.csv

# Excel形式でファイル出力
python test_spec_analytics.py input_sample/sample1.xlsx -o results.xlsx

# 複数ファイル処理でCSV出力
python test_spec_analytics.py input_sample/ -o summary.csv

# 詳細ログ出力
python test_spec_analytics.py input_sample/sample1.xlsx -v

# TSV形式でクリップボードにコピー
python test_spec_analytics.py input_sample/sample1.xlsx -p

# クリップボードのみに出力
python test_spec_analytics.py input_sample/sample1.xlsx -P

# 日付範囲フィルタ
python test_spec_analytics.py --date-range 2024-01-15 2024-01-20 input_sample/sample1.xlsx

# 担当者フィルタ
python test_spec_analytics.py --assignee 田中 input_sample/sample1.xlsx

# 結果タイプフィルタ
python test_spec_analytics.py --result-type Pass Fail input_sample/sample1.xlsx

# 環境フィルタ
python test_spec_analytics.py --environment セット1 input_sample/sample1.xlsx

# 複合フィルタリング
python test_spec_analytics.py --date-range 2024-01-15 2024-01-20 --assignee 田中 --result-type Pass input_sample/sample1.xlsx
```

### コマンドラインオプション

| オプション | 短縮形 | 説明 | デフォルト値 |
|------------|--------|------|--------------|
| `path` | - | 集計対象のファイルまたはフォルダのパス | 必須 |
| `-c, --config` | `-c` | 設定ファイルのパス | `config.json` |
| `-l, --list` | `-l` | プロジェクトリストファイルのパス（JSON/YAML/TXT形式） | なし |
| `-f, --output-format` | `-f` | 出力形式（table/json/csv/excel） | `table` |
| `-o, --output-file` | `-o` | 出力ファイルパス | なし（コンソール出力のみ） |
| `-j, --json-output` | `-j` | JSON形式で出力 | `false` |
| `-v, --verbose` | `-v` | 詳細ログ出力 | `false` |
| `-p, --clipboard` | `-p` | TSV形式でクリップボードにコピー | `false` |
| `-P, --clipboard-only` | `-P` | クリップボードのみに出力（コンソール出力を抑制） | `false` |
| `--date-range` | - | 日付範囲フィルタ（YYYY-MM-DD形式、終了日は省略可能） | なし |
| `--assignee` | - | 担当者フィルタ（部分一致） | なし |
| `--exact-match` | - | 担当者・環境フィルタで完全一致を使用 | `false` |
| `--result-type` | - | 結果タイプフィルタ（複数指定可能） | なし |
| `--environment` | - | 環境フィルタ（部分一致） | なし |
| `-h, --help` | `-h` | ヘルプ表示 | - |

## 出力形式

### テーブル形式出力（デフォルト）

```
==================================================
Summary Results
==================================================

File: input_sample/sample1.xlsx
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

### JSON形式出力

```json
{
  "file": "input_sample/sample1.xlsx",
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

### CSV形式出力

CSV形式でファイルに出力する場合、以下のような構造でデータが出力されます：

**単一ファイル処理の場合**:
- TOTAL RESULTS: 集計結果のサマリー
- STATISTICS: 統計情報
- DAILY BREAKDOWN: 日別集計
- BY NAME: 担当者別集計
- BY ENVIRONMENT: 環境別集計

**複数ファイル処理の場合**:
- SUMMARY TOTAL RESULTS: 統合集計結果
- SUMMARY STATISTICS: 統合統計情報
- INDIVIDUAL FILES: 各ファイルのサマリー

### Excel形式出力

Excel形式でファイルに出力する場合、複数のシートに分けてデータが整理されます：

**単一ファイル処理の場合**:
1. TOTAL RESULTS - 集計結果のサマリー
2. STATISTICS - 統計情報
3. DAILY BREAKDOWN - 日別集計
4. BY NAME - 担当者別集計
5. BY ENVIRONMENT - 環境別集計
6. METADATA - ファイル情報・処理条件

**複数ファイル処理の場合**:
1. SUMMARY TOTAL RESULTS - 統合集計結果
2. SUMMARY STATISTICS - 統合統計情報
3. INDIVIDUAL FILES - 各ファイルのサマリー
4. DAILY BREAKDOWN - 統合日別集計
5. BY NAME - 統合担当者別集計
6. BY ENVIRONMENT - 統合環境別集計
7. METADATA - 処理情報・フィルタ条件

### ファイル名の自動生成

フィルタリング条件を指定した場合、ファイル名に条件が自動的に含まれます：

```bash
# 基本出力
python test_spec_analytics.py -o results.xlsx sample1.xlsx
# → results.xlsx

# 日付フィルタ
python test_spec_analytics.py -o results.xlsx --date-range 2024-01-15 2024-01-20 sample1.xlsx
# → results_2024-01-15_to_2024-01-20.xlsx

# 複合フィルタ
python test_spec_analytics.py -o results.xlsx --date-range 2024-01-15 2024-01-20 --assignee 田中 sample1.xlsx
# → results_2024-01-15_to_2024-01-20_田中.xlsx
```

## 設定ファイル仕様

### config.json

```json
{
  "read_definition": {
    "sheet_search_keys": ["テスト項目"],
    "sheet_search_ignores": [],
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
- `sheet_search_keys`: 対象シートを検索するキーワード
- `header`: ヘッダー行の検索設定
- `result_row`: 結果列の検索設定
- `person_row`: 担当者列の検索設定
- `date_row`: 日付列の検索設定
- `plan_row`: 計画列の検索設定
- `excluded`: 除外対象のキーワード

#### test_status
- `results`: 結果タイプの一覧（表示順序）
- `completed_results`: 完了として扱う結果タイプ
- `executed_results`: 消化として扱う結果タイプ
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
テストケース1   Pass    田中     2024-01-15 2024-01-10
テストケース2   Fail    佐藤     2024-01-16 2024-01-10
テストケース3   Blocked 鈴木     2024-01-17 2024-01-10
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
TestSpecAnalyticsCLI/
├── test_spec_analytics.py  # メインCLI
├── config.json             # 設定ファイル
├── utils/                  # ユーティリティ
│   ├── ReadData.py        # データ読み取り
│   ├── OpenpyxlWrapper.py # Excel操作
│   └── Logger.py          # ログ機能
├── input_sample/          # サンプルデータ
└── assets/               # アセット
    └── logo.txt          # ロゴ
```

### 拡張ポイント
- `utils/ReadData.py`: データ読み取りロジックのカスタマイズ
- `config.json`: 設定による動作のカスタマイズ
- `test_spec_analytics.py`: 出力形式のカスタマイズ

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能要望は、GitHubのIssueでお知らせください。
Pull Requestも歓迎します。

## 更新履歴

- v1.0.0: 初期リリース
  - 基本的な集計機能
  - テーブル・JSON出力
  - エラーハンドリング
  - 設定ファイル対応 