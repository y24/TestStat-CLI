import os
from pathlib import Path
from datetime import datetime
from collections import OrderedDict
from collections import defaultdict

def find_colnum_by_keyword(lst, keyword:str, ignore_words=None):
    if ignore_words is None:
        ignore_words = []
    return [i + 1 for i, item in enumerate(lst) if item and keyword in str(item) and str(item) not in ignore_words]


def find_colnum_by_keywords(lst, keywords:list[str], ignore_words=None):
    if ignore_words is None:
        ignore_words = []
    return [i + 1 for i, item in enumerate(lst) if item and any(kw in str(item) for kw in keywords) and str(item) not in ignore_words]


def transpose_lists(*lists):
    return [list(row) for row in zip(*lists)]


def check_lists_equal_length(*lists):
    """
    任意の数のリストを受け取り、それらの要素数がすべて同じかどうかを判定する
    
    :param lists: 可変長引数としてリストを受け取る
    :return: すべてのリストの長さが同じ場合は True、異なる場合は False
    """
    if not lists:
        return True  # 空の入力の場合は True を返す
    
    # すべてのリストが空の場合は False を返す
    if all(len(lst) == 0 for lst in lists):
        return False

    first_length = len(lists[0])
    return all(len(lst) == first_length for lst in lists)


def get_ext_from_path(filepath:str):
    return os.path.splitext(filepath)[1][1:]


def get_filename_from_path(filepath:str):
    return os.path.basename(filepath)


def is_empty(obj):
    """
    再帰的にオブジェクトが空かどうかを判定する
    
    - 空の辞書、リスト、ネストされた空の辞書・リストは "空" と判定
    - 文字列、数値、None などは "空でない" と判定
    
    :param obj: 判定対象のオブジェクト
    :return: 空なら True、そうでなければ False
    """
    if isinstance(obj, dict):
        # 辞書の場合、すべてのキーが空と判定されたら空
        return all(is_empty(value) for value in obj.values())
    
    elif isinstance(obj, list):
        # リストの場合、すべての要素が空と判定されたら空
        return all(is_empty(item) for item in obj)
    
    # 空の辞書やリストを除いた場合、その他のオブジェクトは空ではない
    return False


def is_empty_recursive(obj):
    if not isinstance(obj, dict):
        return False  # そもそも辞書でない場合は空ではないと判定

    # 値がすべて空の辞書（再帰的にチェック）なら空とみなす
    return all(is_empty_recursive(v) if isinstance(v, dict) else False for v in obj.values())


def get_relative_path(full_path: str, base_dir: str) -> str:
    """
    指定した基準ディレクトリ以降のパスを取得する
    
    Args:
        full_path (str): フルパス
        base_dir (str): 基準ディレクトリ
    
    Returns:
        str: 基準ディレクトリ以降の相対パス
    """
    full_path = Path(full_path).resolve()
    base_dir = Path(base_dir).resolve()
    
    if base_dir not in full_path.parents:
        raise ValueError(f"指定されたパス '{full_path}' は、基準ディレクトリ '{base_dir}' に含まれていません。")
    return str(full_path.relative_to(base_dir))


def get_relative_directory_path(full_path: str, base_dir: str) -> str:
    """
    指定したディレクトリ(base_dir) 以降のパスを取得する
    """
    # 絶対パスに変換して正規化
    full_path = os.path.abspath(full_path)
    base_dir = os.path.abspath(base_dir)

    # base_dir が file_path の先頭部分と一致するか確認
    if not full_path.startswith(base_dir):
        raise ValueError("指定したディレクトリ(base_dir)が、ファイルのパス内に見つかりません。")

    # base_dir の長さを取得し、それ以降のパスを取得
    relative_path = full_path[len(base_dir):].lstrip(os.sep)

    # ディレクトリ部分のみ取得
    return os.path.dirname(relative_path)

def sort_nested_dates_desc(data):
    """
    一番上の階層のキーはそのままで、その下のキー（日付）を降順でソートする
    """
    sorted_data = {}
    for env, dates in data.items():
        sorted_data[env] = OrderedDict(sorted(dates.items(), key=lambda x: x[0], reverse=True))
    return sorted_data

def sort_by_master(master_list, input_list):
    """
    指定されたマスタリストの順番に基づいて、入力リストを並び替える
    """
    return sorted(input_list, key=lambda x: master_list.index(x) if x in master_list else float('inf'))

def meke_rate_text(value1:int, value2:int):
    # パーセンテージ表示用の文字列を生成
    if value2:
        rate = (value1 / value2) * 100
        # return f"{rate:.1f}%"
        if rate < 100:
            return f"{rate:.0f}%"
        else:
            return "100%"
    else:
        return "--"

def sum_values(list, param:str):
    # オブジェクト配列の各キーごとに合計値を計算
    result = defaultdict(int)
    for entry in list:
        # パラメータのキーが存在しない場合はスキップ
        if param not in entry:
            continue
        for key, value in entry[param].items():
            result[key] += value
    return dict(result)

def safe_divide(a:int, b:int):
    return a / b if b else None  # bが0またはNoneならNoneを返す

def filter_objects(obj_list:list[dict], exclude_keys:list[str]):
    """
    入力されたオブジェクト配列から、指定されたキーのいずれかを含まないオブジェクトのみをフィルタする。

    :param obj_list: list[dict] - オブジェクト（辞書）のリスト
    :param exclude_keys: list[str] - 除外したいキーのリスト
    :return: list[dict] - 指定されたキーを含まないオブジェクトのリスト
    """
    return [obj for obj in obj_list if not any(key in obj for key in exclude_keys)]

def initialize_dict(keys):
    """
    指定されたキーのリストを受け取り、すべての値を0にした辞書を作成
    
    Args:
        keys (list): 辞書のキーとなる文字列のリスト。
    
    Returns:
        dict: 各キーが0を持つ辞書。
    """
    return {key: 0 for key in keys}

def find_key_by_name(data: dict, target_name: str) -> str:
    for key, value in data.items():
        if value.get("name") == target_name:
            return key
    return None  # 見つからなかった場合

def get_today_str():
    return datetime.today().strftime("%Y-%m-%d")

def simplify_date(date_str: str) -> str:
    """
    yyyy-MM-dd形式の日付文字列をM/d形式に変換する
    
    Args:
        date_str (str): 'yyyy-MM-dd'形式の日付文字列
        
    Returns:
        str: 'M/d'形式の日付文字列（例：3/25, 12/1）
    """
    if not date_str:
        return "-"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.month}/{dt.day}"
    except ValueError:
        return date_str  # パース失敗時は元の文字列を返す

def get_latest_time(data, key="last_loaded"):
    """
    各ファイルの指定された日時キーから最も遅い日時を取得する
    
    Args:
        data (list): ファイルデータのリスト
        key (str): 日時を取得するキー名。デフォルトは"last_loaded"
        
    Returns:
        str: 最も遅い日時（YYYY-MM-DD HH:MM:SS形式）
    """
    from datetime import datetime
    
    # 指定されたキーの日時が存在するファイルのみを抽出
    valid_times = [
        item[key] 
        for item in data 
        if key in item and item[key]
    ]
    
    if not valid_times:
        return ""
        
    # 日時文字列をdatetimeオブジェクトに変換して比較
    latest_time = max(
        datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S") 
        for time_str in valid_times
    )
    
    return latest_time.strftime("%Y-%m-%d %H:%M:%S")
