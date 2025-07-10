import json
from utils import ReadData
import sys

def print_table(headers, rows):
    """テーブル形式でデータを出力"""
    if not rows:
        return
    
    # 列幅を計算
    col_widths = []
    for i in range(len(headers)):
        max_width = len(str(headers[i]))
        for row in rows:
            max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width)
    
    # ヘッダー行
    header_line = "│ " + " │ ".join(f"{str(h):<{w}}" for h, w in zip(headers, col_widths)) + " │"
    separator = "├─" + "─┼─".join("─" * w for w in col_widths) + "─┤"
    top_border = "┌─" + "─┬─".join("─" * w for w in col_widths) + "─┐"
    bottom_border = "└─" + "─┴─".join("─" * w for w in col_widths) + "─┘"
    
    print(top_border)
    print(header_line)
    print(separator)
    
    # データ行
    for row in rows:
        data_line = "│ " + " │ ".join(f"{str(cell):<{w}}" for cell, w in zip(row, col_widths)) + " │"
        print(data_line)
    
    print(bottom_border)

def format_output(result, filepath):
    """集計結果を美しいテーブル形式で出力"""
    print("=" * 50)
    print("TestSpecAnalytics Results")
    print("=" * 50)
    print()
    
    if "error" in result:
        print(f"ERROR: {result['error']['message']}")
        return
    
    # 基本情報
    print(f"File: {filepath}")
    print(f"Total Cases: {result['stats']['all']}")
    print(f"Available Cases: {result['stats']['available']}")
    print(f"Excluded Cases: {result['stats']['excluded']}")
    print()
    
    # 統計テーブル
    print("STATISTICS:")
    stats_headers = ["Metric", "Count"]
    stats_rows = [
        ["All", result['stats']['all']],
        ["Available", result['stats']['available']],
        ["Executed", result['stats']['executed']],
        ["Completed", result['stats']['completed']],
        ["Incompleted", result['stats']['incompleted']],
        ["Planned", result['stats']['planned']]
    ]
    print_table(stats_headers, stats_rows)
    print()
    
    # 実施状況
    print(f"STATUS: {result['run']['status']}")
    if result['run']['start_date']:
        print(f"Start Date: {result['run']['start_date']}")
    if result['run']['last_update']:
        print(f"Last Update: {result['run']['last_update']}")
    print()
    
    # 日別集計
    if result['daily']:
        print("DAILY BREAKDOWN:")
        daily_headers = ["Date"]
        # 結果タイプを取得（Pass, Fail, Blocked等）
        result_types = set()
        for date_data in result['daily'].values():
            result_types.update(date_data.keys())
        result_types = sorted([rt for rt in result_types if rt not in ['完了数', '消化数', '計画数']])
        daily_headers.extend(result_types)
        daily_headers.append("Total")
        
        daily_rows = []
        for date in sorted(result['daily'].keys()):
            row = [date]
            total = 0
            for rt in result_types:
                count = result['daily'][date].get(rt, 0)
                row.append(count)
                total += count
            row.append(total)
            daily_rows.append(row)
        
        print_table(daily_headers, daily_rows)
        print()
    
    # 担当者別集計
    if result['by_name']:
        print("BY NAME:")
        name_headers = ["Date"]
        # 担当者名を取得
        names = set()
        for date_data in result['by_name'].values():
            names.update(date_data.keys())
        names = sorted(names)
        name_headers.extend(names)
        name_headers.append("Total")
        
        name_rows = []
        for date in sorted(result['by_name'].keys()):
            row = [date]
            total = 0
            for name in names:
                count = result['by_name'][date].get(name, 0)
                row.append(count)
                total += count
            row.append(total)
            name_rows.append(row)
        
        print_table(name_headers, name_rows)
        print()
    
    # 環境別集計
    if result['by_env']:
        print("BY ENVIRONMENT:")
        env_headers = ["Environment"]
        # 結果タイプを取得
        result_types = set()
        for env_data in result['by_env'].values():
            if isinstance(env_data, dict):
                for key, value in env_data.items():
                    if key not in ['完了数', '消化数', '計画数'] and isinstance(value, (int, float)):
                        result_types.add(key)
        result_types = sorted(result_types)
        env_headers.extend(result_types)
        env_headers.append("Total")
        
        env_rows = []
        for env_name in sorted(result['by_env'].keys()):
            row = [env_name]
            total = 0
            env_data = result['by_env'][env_name]
            if isinstance(env_data, dict):
                for rt in result_types:
                    count = env_data.get(rt, 0)
                    if isinstance(count, (int, float)):
                        row.append(count)
                        total += count
                    else:
                        row.append(0)
                row.append(total)
                env_rows.append(row)
        
        if env_rows:
            print_table(env_headers, env_rows)
            print()

if __name__ == "__main__":
    # 設定ファイル読み込み
    with open("config.json", encoding="utf-8") as f:
        settings = json.load(f)

    # 仮: ファイル名を直書き
    filepath = "input_sample/sample1.xlsx"

    # 集計実行
    result = ReadData.aggregate_results(filepath, settings)

    # 結果出力（美しいテーブル形式）
    format_output(result, filepath) 