import json
import urllib.request
import urllib.error

def update_subtask_progress(base_url, subtask_id, progress_percent, logger=None, **kwargs):
    """
    WBS管理ツールのサブタスクを更新するAPIを呼び出します。
    
    Args:
        base_url (str): APIのベースURL
        subtask_id (int/str): 更新対象のサブタスクID
        progress_percent (int/float): 進捗率 (0〜100)
        logger (VerboseLogger, optional): ロガー
        **kwargs: その他の更新パラメータ (status_id, memo, actual_start_date, actual_end_date など)
        
    Returns:
        tuple: (success (bool), error_message (str))
    """
    if not base_url or not subtask_id:
        return False, "APIのベースURLまたはサブタスクIDが設定されていません。"
        
    url = f"{base_url.rstrip('/')}/subtasks/{subtask_id}"
    
    # ペイロードの構築（進捗率のみ必須とし、その他は拡張用kwargsとして受け取る）
    payload = {
        "progress_percent": int(progress_percent)
    }
    
    # 拡張パラメータを追加
    for key, value in kwargs.items():
        if value is not None:
            payload[key] = value
            
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='PATCH')
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 204):
                if logger:
                    logger.log(f"WBSサブタスク({subtask_id})の進捗を更新しました: {payload}")
                return True, ""
            else:
                msg = f"APIエラー: ステータスコード {response.status}"
                if logger:
                    logger.log(msg)
                return False, msg
    except urllib.error.URLError as e:
        msg = f"APIへの接続に失敗しました: {e}"
        if logger:
            logger.log(msg)
        return False, msg
