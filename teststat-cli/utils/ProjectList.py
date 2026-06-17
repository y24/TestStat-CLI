import os
import yaml

from utils import RemoteSource

# YAMLライブラリのインポート確認
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

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

    testing_id = project_data.get("testing_id", None)
    if testing_id is not None and not isinstance(testing_id, int):
        raise ValueError(f"プロジェクトリストファイルの形式が不正です: 'testing_id'は整数で指定してください")
    
    # ファイル情報の検証と抽出
    file_info_list = []
    for i, file_info in enumerate(project_data["files"]):
        if not isinstance(file_info, dict):
            raise ValueError(f"プロジェクトリストファイルの形式が不正です: files[{i}]が辞書ではありません")
        
        if "path" not in file_info or "label" not in file_info:
            raise ValueError(f"プロジェクトリストファイルの形式が不正です: files[{i}]に'path'または'label'キーが見つかりません")
        
        # リモート URL は normpath を適用せず、そのまま保持する
        if RemoteSource.is_remote_path(file_info["path"]):
            item = {
                "path": file_info["path"].strip(),
                "label": file_info["label"],
                "is_remote": True
            }
        else:
            item = {
                "path": os.path.normpath(file_info["path"]),
                "label": file_info["label"],
                "is_remote": False
            }
        
        # オプション設定の追加
        if "target_sheets" in file_info:
            item["target_sheets"] = file_info["target_sheets"]
        if "ignore_sheets" in file_info:
            item["ignore_sheets"] = file_info["ignore_sheets"]
        if "include_hidden_sheets" in file_info:
            item["include_hidden_sheets"] = file_info["include_hidden_sheets"]
        if "subtask_id" in file_info:
            item["subtask_id"] = file_info["subtask_id"]
        if "target_environments" in file_info:
            item["target_environments"] = file_info["target_environments"]
        if "ignore_environments" in file_info:
            item["ignore_environments"] = file_info["ignore_environments"]
            
        file_info_list.append(item)
    
    if not file_info_list:
        raise ValueError(f"プロジェクトリストファイルに有効なファイルが含まれていません: {list_file_path}")
    
    return {
        "project_name": project_data["project_name"],
        "testing_id": testing_id,
        "files": file_info_list,
        "subtask_id": project_data.get("subtask_id", None)
    }

def read_paths_from_list_file(list_file_path):
    """リストファイルからパスを読み取る（互換性のため）"""
    project_data = read_project_list_file(list_file_path)
    return [file_info["path"] for file_info in project_data["files"]]
