#!/usr/bin/env python3
"""
TestStat-CLI exe配布パッケージ作成スクリプト
ビルドされたexeファイルと必要なファイルをパッケージ化します
"""

import os
import sys
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

def create_distribution_package():
    """配布用パッケージを作成"""
    print("配布用パッケージを作成しています...")
    
    # 配布ディレクトリの作成
    dist_dir = "dist_package"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # exeファイルの存在確認
    exe_path = "dist/tstat.exe"
    if not os.path.exists(exe_path):
        print("ERROR: exeファイルが見つかりません。先にビルドを実行してください。")
        print("実行方法: python build_exe.py build")
        return False
    
    # 必要なファイルをコピー
    files_to_copy = [
        ("dist/tstat.exe", "tstat.exe"),
        ("config.json", "config.json"),
        ("dist_config.json", "config_example.json"),
        ("README_EXE.md", "README.md"),
        ("assets/logo.txt", "assets/logo.txt")
    ]
    
    for src, dst in files_to_copy:
        if os.path.exists(src):
            dst_path = os.path.join(dist_dir, dst)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src, dst_path)
            print(f"コピー: {src} -> {dst}")
        else:
            print(f"WARNING: ファイルが見つかりません: {src}")
    
    # サンプルファイルをコピー
    sample_dirs = ["input_sample"]
    for sample_dir in sample_dirs:
        if os.path.exists(sample_dir):
            dst_sample_dir = os.path.join(dist_dir, "samples", sample_dir)
            shutil.copytree(sample_dir, dst_sample_dir)
            print(f"コピー: {sample_dir} -> samples/{sample_dir}")
    
    # 使用方法の説明ファイルを作成
    create_usage_file(dist_dir)
    
    # ZIPファイルを作成
    create_zip_package(dist_dir)
    
    print(f"\n配布パッケージが作成されました: {dist_dir}")
    return True

def create_usage_file(dist_dir):
    """使用方法の説明ファイルを作成"""
    usage_content = """# TestStat-CLI 使用方法

## 基本的な使用方法

1. コマンドプロンプトを開く
2. このフォルダに移動
3. 以下のコマンドを実行

### ヘルプ表示
```
tstat.exe --help
```

### 単一ファイルの集計
```
tstat.exe "path/to/test_spec.xlsx"
```

### ディレクトリ内の全Excelファイルを集計
```
tstat.exe "path/to/test_folder"
```

### 設定ファイルを指定
```
tstat.exe "test_spec.xlsx" -c config.json
```

### 結果をCSVファイルに出力
```
tstat.exe "test_spec.xlsx" -o "output.csv" -f csv
```

### 結果をExcelファイルに出力
```
tstat.exe "test_spec.xlsx" -o "output.xlsx" -f excel
```

### クリップボードにコピー
```
tstat.exe "test_spec.xlsx" -p
```

## フィルタリング機能

### 日付範囲フィルタ
```
tstat.exe "test_spec.xlsx" --date-range "2024-01-01" "2024-01-31"
```

### 担当者フィルタ
```
tstat.exe "test_spec.xlsx" --tester "テスト太郎"
```

### 結果タイプフィルタ
```
tstat.exe "test_spec.xlsx" --result-type Pass Fail
```

### 環境フィルタ
```
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

詳細は `README.md` を参照してください。
"""
    
    usage_file = os.path.join(dist_dir, "使用方法.txt")
    with open(usage_file, 'w', encoding='utf-8') as f:
        f.write(usage_content)
    
    print(f"作成: 使用方法.txt")

def create_zip_package(dist_dir):
    """ZIPパッケージを作成"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"TestStat-CLI_v1.0.0_{timestamp}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname)
    
    print(f"ZIPパッケージを作成しました: {zip_filename}")

def main():
    """メイン関数"""
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        # クリーンアップ
        cleanup_targets = ["dist_package", "TestStat-CLI_*.zip"]
        for target in cleanup_targets:
            if os.path.exists(target):
                if os.path.isdir(target):
                    shutil.rmtree(target)
                else:
                    os.remove(target)
                print(f"削除: {target}")
        print("クリーンアップが完了しました")
    else:
        # パッケージ作成
        create_distribution_package()

if __name__ == "__main__":
    main() 