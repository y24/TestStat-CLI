import os
import yaml
from datetime import datetime

# YAMLライブラリのインポート確認
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

def update_project_list_last_loaded(list_file_path, timestamp=None):
    """プロジェクトリストファイルのlast_loaded値を更新する"""
    try:
        if not YAML_AVAILABLE:
            print(f"WARNING: YAMLファイルの更新に失敗しました。PyYAMLライブラリが必要です: {list_file_path}")
            return False

        file_extension = os.path.splitext(list_file_path)[1].lower()
        if file_extension not in ['.yaml', '.yml']:
            print(f"WARNING: サポートされていないファイル形式です: {file_extension} (対応形式: .yaml, .yml)")
            return False
        
        with open(list_file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if data and "project" in data:
            data["project"]["last_loaded"] = timestamp if timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(list_file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            return True
        else:
            print(f"WARNING: プロジェクトリストファイルの形式が不正です: {list_file_path}")
            return False
            
    except Exception as e:
        print(f"WARNING: プロジェクトリストファイルの更新に失敗しました: {list_file_path}, 詳細: {e}")
        return False

def read_project_list_file(list_file_path):
    """プロジェクトリストファイルからファイル情報を読み取る"""
    file_extension = os.path.splitext(list_file_path)[1].lower()
    
    if file_extension in ['.yaml', '.yml']:
        return read_yaml_project_list(list_file_path)
    else:
        raise ValueError(f"サポートされていないファイル形式です: {file_extension} (対応形式: .yaml, .yml)")

def read_yaml_project_list(list_file_path):
    """プロジェクトリストファイル（YAML）を読み取る"""
    if not YAML_AVAILABLE:
        raise ImportError("YAMLファイルを処理するにはPyYAMLライブラリが必要です。pip install PyYAML でインストールしてください。")

    try:
        with open(list_file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"プロジェクトリストファイルが見つかりません: {list_file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"YAMLファイルの形式が不正です: {list_file_path}, 詳細: {e}")
    except Exception as e:
        raise Exception(f"プロジェクトリストファイルの読み込みに失敗しました: {list_file_path}, 詳細: {e}")
    
    # データ構造の検証
    if not isinstance(data, dict) or "project" not in data:
        raise ValueError(f"プロジェクトリストファイルの形式が不正です: 'project'キーが見つかりません")
    
    project_data = data["project"]
    
    # 必須フィールドの検証
    required_fields = ["project_name", "files"]
    for field in required_fields:
        if field not in project_data:
            raise ValueError(f"プロジェクトリストファイルの形式が不正です: '{field}'キーが見つかりません")
    
    if not isinstance(project_data["files"], list):
        raise ValueError(f"プロジェクトリストファイルの形式が不正です: 'files'がリストではありません")
    
    # ファイル情報の検証と抽出
    file_info_list = []
    for i, file_info in enumerate(project_data["files"]):
        if not isinstance(file_info, dict):
            raise ValueError(f"プロジェクトリストファイルの形式が不正です: files[{i}]が辞書ではありません")
        
        if "path" not in file_info or "label" not in file_info:
            raise ValueError(f"プロジェクトリストファイルの形式が不正です: files[{i}]に'path'または'label'キーが見つかりません")
        
        file_path = os.path.normpath(file_info["path"])
        item = {
            "path": file_path,
            "label": file_info["label"]
        }
        
        # オプション設定の追加
        if "target_sheets" in file_info:
            item["target_sheets"] = file_info["target_sheets"]
        if "ignore_sheets" in file_info:
            item["ignore_sheets"] = file_info["ignore_sheets"]
            
        file_info_list.append(item)
    
    if not file_info_list:
        raise ValueError(f"プロジェクトリストファイルに有効なファイルが含まれていません: {list_file_path}")
    
    return {
        "project_name": project_data["project_name"],
        "files": file_info_list,
        "last_loaded": project_data.get("last_loaded", "")
    }

def read_paths_from_list_file(list_file_path):
    """リストファイルからパスを読み取る（互換性のため）"""
    project_data = read_project_list_file(list_file_path)
    return [file_info["path"] for file_info in project_data["files"]]
