# TestSpecAnalyticsCLI 要件定義書

## 1. 概要

既存の`ReadData.py`モジュールを基に、Windowsコマンドラインで実行可能なCLIツールを開発します。Excelファイル（.xlsx）からテスト結果データを読み取り、集計結果をコンソールに表示するツールです。

## 2. 基本機能

### 2.1 コア機能
- Excelファイル（.xlsx）の読み取り
- `ReadData.py`と同じロジックによるデータ集計
- 集計結果のコンソール表示（テーブル形式）
- JSON形式での出力オプション

### 2.2 ファイル処理オプション
- 単一ファイル処理：指定されたxlsxファイルを処理
- フォルダ一括処理：指定されたフォルダ内の全xlsxファイルを処理

## 3. コマンドライン仕様

### 3.1 基本コマンド形式
```bash
python test_spec_analytics.py [オプション] [ファイルパス/フォルダパス]
```

### 3.2 オプション一覧
| オプション | 短縮形 | 説明 | デフォルト値 |
|------------|--------|------|--------------|
| `--config` | `-c` | 設定ファイルのパス | `config.json` |
| `--output-format` | `-f` | 出力形式（table/json） | `table` |
| `--json-output` | `-j` | JSON形式で出力 | `false` |
| `--verbose` | `-v` | 詳細ログ出力 | `false` |
| `--help` | `-h` | ヘルプ表示 | - |

### 3.3 使用例
```bash
# 単一ファイル処理（テーブル形式）
python test_spec_analytics.py sample1.xlsx

# 単一ファイル処理（JSON形式）
python test_spec_analytics.py -j sample1.xlsx

# フォルダ一括処理
python test_spec_analytics.py input_sample/

# カスタム設定ファイル使用
python test_spec_analytics.py -c custom_config.json sample1.xlsx

# 詳細ログ付き
python test_spec_analytics.py -v sample1.xlsx
```

## 4. 設定ファイル仕様

### 4.1 設定ファイル形式
- JSON形式
- デフォルト：`config.json`（ツールと同じディレクトリ）
- カスタム設定ファイルも指定可能

### 4.2 設定項目
現在の`config.json`の構造をそのまま使用：
- `read_definition`: データ読み取り定義
- `test_status`: テストステータス定義

## 5. 出力仕様

### 5.1 テーブル形式出力

#### 単一ファイル処理の場合
```
==========================================
TestSpecAnalytics Results
==========================================

File: sample1.xlsx
Total Cases: 150
Available Cases: 145
Excluded Cases: 5

STATISTICS:
┌─────────────┬─────────┐
│ Metric      │ Count   │
├─────────────┼─────────┤
│ All         │ 150     │
│ Available   │ 145     │
│ Executed    │ 120     │
│ Completed   │ 100     │
│ Incompleted │ 25      │
│ Planned     │ 80      │
└─────────────┴─────────┘

STATUS: In Progress
Start Date: 2024-01-15
Last Update: 2024-01-20

DAILY BREAKDOWN:
┌────────────┬─────────┬─────────┬─────────┬─────────┐
│ Date       │ Pass    │ Fail    │ Blocked │ Total   │
├────────────┼─────────┼─────────┼─────────┼─────────┤
│ 2024-01-15 │ 10      │ 2       │ 1       │ 13      │
│ 2024-01-16 │ 15      │ 1       │ 0       │ 16      │
└────────────┴─────────┴─────────┴─────────┴─────────┘

BY NAME:
┌────────────┬─────────┬─────────┬─────────┬─────────┐
│ Date       │ 田中    │ 佐藤    │ 鈴木    │ Total   │
├────────────┼─────────┼─────────┼─────────┼─────────┤
│ 2024-01-15 │ 8       │ 3       │ 2       │ 13      │
│ 2024-01-16 │ 10      │ 4       │ 2       │ 16      │
└────────────┴─────────┴─────────┴─────────┴─────────┘

BY ENVIRONMENT:
┌─────────────┬─────────┬─────────┬─────────┬─────────┐
│ Environment │ Pass    │ Fail    │ Blocked │ Total   │
├─────────────┼─────────┼─────────┼─────────┼─────────┤
│ セット1     │ 25      │ 3       │ 1       │ 29      │
│ セット2     │ 20      │ 2       │ 0       │ 22      │
└─────────────┴─────────┴─────────┴─────────┴─────────┘
```

#### 複数ファイル処理の場合
```
==========================================
TestSpecAnalytics Results Summary
==========================================

Processed Files: 3
Total Processing Time: 2.3s

SUMMARY STATISTICS:
┌─────────────┬─────────┬─────────┬─────────┐
│ Metric      │ Total   │ Avg     │ Max     │
├─────────────┼─────────┼─────────┼─────────┤
│ All Cases   │ 450     │ 150     │ 200     │
│ Available   │ 435     │ 145     │ 190     │
│ Executed    │ 360     │ 120     │ 150     │
│ Completed   │ 300     │ 100     │ 120     │
│ Incompleted │ 75      │ 25      │ 30      │
│ Planned     │ 240     │ 80      │ 100     │
└─────────────┴─────────┴─────────┴─────────┘

OVERALL STATUS: In Progress
Earliest Start Date: 2024-01-10
Latest Update: 2024-01-25

==========================================
File: sample1.xlsx
==========================================

Total Cases: 150
Available Cases: 145
Excluded Cases: 5

STATISTICS:
┌─────────────┬─────────┐
│ Metric      │ Count   │
├─────────────┼─────────┤
│ All         │ 150     │
│ Available   │ 145     │
│ Executed    │ 120     │
│ Completed   │ 100     │
│ Incompleted │ 25      │
│ Planned     │ 80      │
└─────────────┴─────────┘

STATUS: In Progress
Start Date: 2024-01-15
Last Update: 2024-01-20

DAILY BREAKDOWN:
┌────────────┬─────────┬─────────┬─────────┬─────────┐
│ Date       │ Pass    │ Fail    │ Blocked │ Total   │
├────────────┼─────────┼─────────┼─────────┼─────────┤
│ 2024-01-15 │ 10      │ 2       │ 1       │ 13      │
│ 2024-01-16 │ 15      │ 1       │ 0       │ 16      │
└────────────┴─────────┴─────────┴─────────┴─────────┘

==========================================
File: sample2.xlsx
==========================================

Total Cases: 200
Available Cases: 190
Excluded Cases: 10

STATISTICS:
┌─────────────┬─────────┐
│ Metric      │ Count   │
├─────────────┼─────────┤
│ All         │ 200     │
│ Available   │ 190     │
│ Executed    │ 150     │
│ Completed   │ 120     │
│ Incompleted │ 40      │
│ Planned     │ 100     │
└─────────────┴─────────┘

STATUS: In Progress
Start Date: 2024-01-10
Last Update: 2024-01-25

DAILY BREAKDOWN:
┌────────────┬─────────┬─────────┬─────────┬─────────┐
│ Date       │ Pass    │ Fail    │ Blocked │ Total   │
├────────────┼─────────┼─────────┼─────────┼─────────┤
│ 2024-01-10 │ 20      │ 5       │ 2       │ 27      │
│ 2024-01-15 │ 25      │ 3       │ 1       │ 29      │
│ 2024-01-25 │ 30      │ 2       │ 0       │ 32      │
└────────────┴─────────┴─────────┴─────────┴─────────┘

==========================================
File: sample3.xlsx
==========================================

Total Cases: 100
Available Cases: 100
Excluded Cases: 0

STATISTICS:
┌─────────────┬─────────┐
│ Metric      │ Count   │
├─────────────┼─────────┤
│ All         │ 100     │
│ Available   │ 100     │
│ Executed    │ 90      │
│ Completed   │ 80      │
│ Incompleted │ 10      │
│ Planned     │ 60      │
└─────────────┴─────────┘

STATUS: Completed
Start Date: 2024-01-12
Last Update: 2024-01-18

DAILY BREAKDOWN:
┌────────────┬─────────┬─────────┬─────────┬─────────┐
│ Date       │ Pass    │ Fail    │ Blocked │ Total   │
├────────────┼─────────┼─────────┼─────────┼─────────┤
│ 2024-01-12 │ 15      │ 1       │ 0       │ 16      │
│ 2024-01-18 │ 20      │ 2       │ 1       │ 23      │
└────────────┴─────────┴─────────┴─────────┴─────────┘
```

### 5.2 JSON形式出力

#### 単一ファイル処理の場合
```json
{
  "file": "sample1.xlsx",
  "stats": {
    "all": 150,
    "excluded": 5,
    "available": 145,
    "executed": 120,
    "completed": 100,
    "incompleted": 25,
    "planned": 80
  },
  "run": {
    "status": "in_progress",
    "start_date": "2024-01-15",
    "last_update": "2024-01-20"
  },
  "daily": {
    "2024-01-15": {
      "Pass": 10,
      "Fail": 2,
      "Blocked": 1,
      "完了数": 13,
      "消化数": 13
    }
  },
  "by_name": {
    "2024-01-15": {
      "田中": 8,
      "佐藤": 3,
      "鈴木": 2
    },
    "2024-01-16": {
      "田中": 10,
      "佐藤": 4,
      "鈴木": 2
    }
  },
  "by_env": {
    "セット1": {
      "Pass": 25,
      "Fail": 3,
      "Blocked": 1,
      "完了数": 29,
      "消化数": 29
    }
  }
}
```

#### 複数ファイル処理の場合
```json
{
  "summary": {
    "processed_files": 3,
    "processing_time": 2.3,
    "total_stats": {
      "all": 450,
      "excluded": 15,
      "available": 435,
      "executed": 360,
      "completed": 300,
      "incompleted": 75,
      "planned": 240
    },
    "overall_status": "in_progress",
    "earliest_start_date": "2024-01-10",
    "latest_update": "2024-01-25"
  },
  "files": [
    {
      "file": "sample1.xlsx",
      "stats": {
        "all": 150,
        "excluded": 5,
        "available": 145,
        "executed": 120,
        "completed": 100,
        "incompleted": 25,
        "planned": 80
      },
      "run": {
        "status": "in_progress",
        "start_date": "2024-01-15",
        "last_update": "2024-01-20"
      },
      "daily": {
        "2024-01-15": {
          "Pass": 10,
          "Fail": 2,
          "Blocked": 1,
          "完了数": 13,
          "消化数": 13
        }
      },
      "by_name": {
        "2024-01-15": {
          "田中": 8,
          "佐藤": 3,
          "鈴木": 2
        }
      },
      "by_env": {
        "セット1": {
          "Pass": 25,
          "Fail": 3,
          "Blocked": 1,
          "完了数": 29,
          "消化数": 29
        }
      }
    },
    {
      "file": "sample2.xlsx",
      "stats": {
        "all": 200,
        "excluded": 10,
        "available": 190,
        "executed": 150,
        "completed": 120,
        "incompleted": 40,
        "planned": 100
      },
      "run": {
        "status": "in_progress",
        "start_date": "2024-01-10",
        "last_update": "2024-01-25"
      },
      "daily": {
        "2024-01-10": {
          "Pass": 20,
          "Fail": 5,
          "Blocked": 2,
          "完了数": 27,
          "消化数": 27
        }
      },
      "by_name": {
        "2024-01-10": {
          "田中": 15,
          "佐藤": 8,
          "鈴木": 4
        }
      },
      "by_env": {
        "セット1": {
          "Pass": 20,
          "Fail": 5,
          "Blocked": 2,
          "完了数": 27,
          "消化数": 27
        }
      }
    },
    {
      "file": "sample3.xlsx",
      "stats": {
        "all": 100,
        "excluded": 0,
        "available": 100,
        "executed": 90,
        "completed": 80,
        "incompleted": 10,
        "planned": 60
      },
      "run": {
        "status": "completed",
        "start_date": "2024-01-12",
        "last_update": "2024-01-18"
      },
      "daily": {
        "2024-01-12": {
          "Pass": 15,
          "Fail": 1,
          "Blocked": 0,
          "完了数": 16,
          "消化数": 16
        }
      },
      "by_name": {
        "2024-01-12": {
          "田中": 10,
          "佐藤": 4,
          "鈴木": 2
        }
      },
      "by_env": {
        "セット1": {
          "Pass": 15,
          "Fail": 1,
          "Blocked": 0,
          "完了数": 16,
          "消化数": 16
        }
      }
    }
  ]
}
```

## 6. エラーハンドリング

### 6.1 エラーケース
- ファイルが見つからない
- 設定ファイルが無効
- Excelファイルの形式エラー
- データ読み取りエラー
- 権限エラー

### 6.2 エラー出力形式
```
ERROR: File not found - sample1.xlsx
ERROR: Invalid configuration file - config.json
ERROR: Excel file format error - corrupted.xlsx
```

## 7. 将来拡張予定

### 7.1 フィルタリング機能
- 特定の日付範囲での集計
- 特定の担当者での集計
- 特定の結果タイプでの集計

### 7.2 出力オプション
- CSV形式出力
- Excel形式出力
- 特定の統計情報のみ出力

### 7.3 バッチ処理
- 複数フォルダの一括処理
- 処理結果のサマリーレポート

## 8. 技術要件

### 8.1 依存関係
- Python 3.7以上
- openpyxl（Excelファイル読み取り）
- argparse（コマンドライン引数処理）
- json（設定ファイル処理）

### 8.2 ファイル構成
```
TestSpecAnalyticsCLI/
├── test_spec_analytics.py    # メインCLIツール
├── config.json        # デフォルト設定ファイル
└── utils/                   # 既存モジュール
    ├── ReadData.py
    ├── OpenpyxlWrapper.py
    ├── TempDir.py
    ├── Utility.py
    └── Logger.py
``` 