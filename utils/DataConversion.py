from utils import Utility, Labels
from collections import defaultdict
import os

def convert_to_2d_array(data, settings):
    # ヘッダーの作成
    base_header = ["ファイル名", "識別子", "環境名", "日付"]
    completed_label = settings["test_status"]["labels"]["completed"]
    executed_label = settings["test_status"]["labels"]["executed"]
    planned_label = settings["test_status"]["labels"]["planned"]
    results = settings["test_status"]["results"]
    out_results = results + [executed_label, completed_label, planned_label]
    header = base_header + out_results

    # 出力用の2次元配列の作成
    out_arr = [header]

    # データの書き込み
    for entry in data:
        file_path = entry.get("file", "")
        # フルパスからファイル名のみを抽出
        file_name = os.path.basename(file_path)
        # identifierを取得（プロジェクトリストファイルから設定された値）
        identifier = entry.get("identifier", "")
        by_env_data = entry.get("by_env", {})
        daily_data = entry.get("daily", {})
        if not Utility.is_empty_recursive(by_env_data):
            # 環境別データがある場合
            for env, env_data in by_env_data.items():
                for date, values in env_data.items():
                    out_arr.append([file_name, identifier, env, date] + [values.get(v, 0) for v in out_results])
        elif not Utility.is_empty_recursive(daily_data):
            # 環境別データがないが日付別データがある場合は、環境名は空で出力
            for date, values in entry.get("daily", {}).items():
                out_arr.append([file_name, identifier, "", date] + [values.get(v, 0) for v in out_results])
        else:
            # 環境別データも日付別データもない場合は、環境名と日付を空で合計データを出力
            total_data = entry.get("total", {})
            stats_data = entry.get("stats", {})
            out_arr.append([file_name, identifier, "", ""] + [total_data.get(v, 0) for v in results] + [stats_data.get("executed", 0), stats_data.get("completed", 0)])
    return out_arr

def create_export_data(input_data: list, settings: dict) -> list:
    """エクスポート用のデータを生成する

    Args:
        input_data: 集計データ
        settings: 設定情報

    Returns:
        list: エクスポート用の2次元配列データ
    """
    # クリップボード出力用のヘッダ
    export_headers = ["No.", "ファイル名", "項目数", "更新日", "完了数", "消化率", "完了率"]
    export_data = [export_headers + settings["test_status"]["results"] + [settings["test_status"]["labels"]["not_run"]]]

    # 各ファイルのデータを追加
    for index, file_data in enumerate(input_data, 1):
        display_data = _extract_file_data(file_data)
        # フルパスからファイル名のみを抽出
        file_name = os.path.basename(file_data['file'])
        export_row = [
            index,  # No.
            file_name,  # ファイル名
            display_data["available"],  # 項目数
            display_data["last_update"] or "",  # 更新日
            display_data["completed"],  # 完了数
            display_data["executed_rate_text"],  # 消化率
            display_data["comp_rate_text"]  # 完了率
        ]

        # エラー時は空文字を設定
        if display_data["on_error"]:
            export_row[4:] = ["", "", ""]  # 完了数、消化率、完了率を空に

        # テスト結果データを追加
        if not display_data["on_error"]:
            export_row += list(display_data["total_data"].values())
            export_row.append(display_data["incompleted"])

        export_data.append(export_row)

    return export_data

def _extract_file_data(file_data: dict) -> dict:
    """ファイルデータから表示用の情報を抽出する
    
    Args:
        file_data: ファイルデータ
        
    Returns:
        dict: 表示用のデータ
    """
    base_info = {
        "on_warning": False,
        "on_error": False,
        "error_type": "",
        "error_message": "",
    }

    # ワーニングの確認
    if "warning" in file_data:
        base_info.update({
            "on_warning": True,
            "error_type": file_data["warning"]["type"],
            "error_message": file_data["warning"]["message"]
        })

    # エラー時はダミーデータを返却
    if "error" in file_data:
        return {
            **base_info,
            "on_error": True,
            "total_data": {
                "error": 0,
                "all": 0,        # エラー時のall追加
                "excluded": 0    # エラー時のexcluded追加
            },
            "state": "???",
            "completed": "",
            "executed": "",
            "available": "",
            "incompleted": 0,
            "comp_rate_text": "",
            "executed_rate_text": "",
            "start_date": "",
            "last_update": "",
            "error_type": file_data["error"]["type"],
            "error_message": file_data["error"]["message"]
        }

    # 正常時のデータ抽出
    stats = file_data["stats"]
    run_data = file_data["run"]
    
    return {
        **base_info,
        "total_data": {
            **file_data["total"]
        },
        "state": run_data["status"],
        "all": stats["all"],
        "excluded": stats["excluded"],
        "completed": stats["completed"],
        "executed": stats["executed"],
        "available": stats["available"],
        "incompleted": stats["incompleted"],
        "comp_rate_text": Labels.make_count_and_rate_text(stats["completed"], stats["available"]),
        "executed_rate_text": Labels.make_count_and_rate_text(stats["executed"], stats["available"]),
        "start_date": run_data["start_date"],
        "last_update": run_data["last_update"]
    }

def aggregate_all_daily(data):
    result = defaultdict(lambda: defaultdict(int))
    for record in data:
        # エラーまたはワーニングのあるデータは除外
        if "error" in record or "warning" in record:
            continue
        daily = record.get("daily", {})
        for date, values in daily.items():
            for k, v in values.items():
                result[date][k] += v
    return {date: dict(stats) for date, stats in result.items()}

def aggregate_all_stats(data):
    result = defaultdict(int)
    for record in data:
        # エラーまたはワーニングのあるデータは除外
        if "error" in record or "warning" in record:
            continue
        stats = record.get("stats", {})
        for k, v in stats.items():
            result[k] += v
    return dict(result)