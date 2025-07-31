# TestStat-CLI

```
  _____         _   ____  _        _      ____ _     ___
 |_   _|__  ___| |_/ ___|| |_ __ _| |_   / ___| |   |_ _|
   | |/ _ \/ __| __\___ \| __/ _` | __| | |   | |    | |
   | |  __/\__ \ |_ ___) | || (_| | |_  | |___| |___ | |
   |_|\___||___/\__|____/ \__\__,_|\__|  \____|_____|___|
```

Excelテスト仕様書からテスト結果を集計するCLIツールです。

## ファイル構成

```
dist/
├── tstat.exe          # メイン実行ファイル
├── config.json        # 設定ファイル
└── assets/
    └── logo.txt       # ロゴファイル
```

## 使用方法

### 基本的な使用方法

```bash
# ヘルプ表示
tstat.exe --help

# 単一ファイルの集計
tstat.exe "path/to/test_spec.xlsx"

# 複数ファイルの集計（複数のxlsxファイルを直接指定）
tstat.exe "path/to/file1.xlsx" "path/to/file2.xlsx" "path/to/file3.xlsx"

# ディレクトリ内の全Excelファイルを集計
tstat.exe "path/to/test_folder"

# プロジェクトリストファイルを使用
tstat.exe -l "path/to/project_list.json"
```

### 出力オプション

```bash
# CSVファイルに出力
tstat.exe "test_spec.xlsx" -o "output.csv" -f csv

# Excelファイルに出力
tstat.exe "test_spec.xlsx" -o "output.xlsx" -f excel

# JSON形式で出力
tstat.exe "test_spec.xlsx" -j

# クリップボードにTSV形式でコピー
tstat.exe "test_spec.xlsx" -p
```

### フィルタリングオプション

```bash
# 日付範囲フィルタ
tstat.exe "test_spec.xlsx" --date-range "2024-01-01" "2024-01-31"

# 担当者フィルタ
tstat.exe "test_spec.xlsx" --tester "テスト太郎"

# 結果タイプフィルタ
tstat.exe "test_spec.xlsx" --result-type Pass Fail

# 環境フィルタ
tstat.exe "test_spec.xlsx" --environment "本番環境"
```

## 設定ファイル

`config.json`ファイルで以下の設定を変更できます：

- **sheet_search_keys**: 検索するシート名のキーワード
- **header**: テストケースIDの列名
- **result_row**: 結果の列名
- **person_row**: 担当者の列名
- **date_row**: 実施日の列名
- **environment_row**: 環境の列名
- **results**: 有効な結果タイプ
- **completed_results**: 完了とみなす結果タイプ
- **executed_results**: 実施済みとみなす結果タイプ

## 複数ファイル処理

複数のxlsxファイルを同時に処理する場合、以下の方法があります：

### 1. 直接指定による複数ファイル処理
```bash
# 複数のxlsxファイルを直接指定
tstat.exe file1.xlsx file2.xlsx file3.xlsx

# パスに空白が含まれる場合は引用符で囲む
tstat.exe "D:\Script\TestStat-CLI\input_sample\sample1.xlsx" "D:\Script\TestStat-CLI\input_sample\sample2_abcdegfg.xlsx"
```

### 2. プロジェクトリストファイルによる複数ファイル処理
複数のファイルを一括処理する場合は、プロジェクトリストファイルを使用できます。

### JSON形式
```json
{
  "project": {
    "project_name": "プロジェクト名",
    "files": [
      {
        "path": "path/to/file1.xlsx",
        "identifier": "file1"
      },
      {
        "path": "path/to/file2.xlsx",
        "identifier": "file2"
      }
    ],
    "last_loaded": "2024-01-01 12:00:00"
  }
}
```

### YAML形式
```yaml
project:
  project_name: プロジェクト名
  files:
    - path: path/to/file1.xlsx
      identifier: file1
    - path: path/to/file2.xlsx
      identifier: file2
  last_loaded: "2024-01-01 12:00:00"
```

### テキスト形式
```
path/to/file1.xlsx
path/to/file2.xlsx
```

### 複数ファイル処理の出力内容
複数ファイルを処理した場合、以下の情報が表示されます：

- **SUMMARY TOTAL RESULTS**: 全ファイルの統合集計結果
- **FILE BREAKDOWN**: 各ファイルの個別サマリー
- **ERROR SUMMARY**: エラーが発生したファイルの一覧
- **OVERALL STATUS**: 全体のステータス情報
- **各ファイルの詳細**: 各ファイルの個別詳細集計

## トラブルシューティング

### よくあるエラー

1. **ファイルが見つからない**
   - パスが正しいか確認してください
   - ファイルが存在するか確認してください

2. **設定ファイルエラー**
   - `config.json`の形式が正しいか確認してください
   - 必須項目が含まれているか確認してください

3. **権限エラー**
   - ファイルの読み取り権限があるか確認してください
   - 出力先ディレクトリの書き込み権限があるか確認してください

### ログ出力

詳細なログを出力するには `-v` オプションを使用してください：

```bash
tstat.exe "test_spec.xlsx" -v
```

## 更新履歴

- v1.0.0: 初回リリース
  - 基本的な集計機能
  - 複数ファイル対応
  - フィルタリング機能
  - 各種出力形式対応 