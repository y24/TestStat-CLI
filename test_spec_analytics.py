import json
from utils import ReadData
import sys
import unicodedata
import argparse
import os
import glob

def get_display_width(text):
    """全角・半角を考慮した表示幅を返す"""
    text = str(text)
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ('F', 'W', 'A'):
            width += 2
        else:
            width += 1
    return width

def pad_display(text, width):
    """全角・半角を考慮して幅を揃える"""
    text = str(text)
    pad = width - get_display_width(text)
    return text + ' ' * pad

def print_table(headers, rows):
    """全角対応テーブル出力"""
    if not rows:
        return
    col_widths = []
    for i in range(len(headers)):
        max_width = get_display_width(headers[i])
        for row in rows:
            max_width = max(max_width, get_display_width(row[i]))
        col_widths.append(max_width)
    # 罫線生成
    header_line = "│ " + " │ ".join(pad_display(h, w) for h, w in zip(headers, col_widths)) + " │"
    separator = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
    top_border = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
    bottom_border = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"
    print(top_border)
    print(header_line)
    print(separator)
    for row in rows:
        data_line = "│ " + " │ ".join(pad_display(cell, w) for cell, w in zip(row, col_widths)) + " │"
        print(data_line)
    print(bottom_border)

def format_output(result, filepath, show_title=True):
    """集計結果を美しいテーブル形式で出力"""
    if show_title:
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
    
    # 総合結果テーブル
    if 'total' in result:
        print("TOTAL RESULTS:")
        total_headers = ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A", "Total"]
        total_row = [
            result['total'].get('Pass', 0),
            result['total'].get('Fixed', 0),
            result['total'].get('Fail', 0),
            result['total'].get('Blocked', 0),
            result['total'].get('Suspend', 0),
            result['total'].get('N/A', 0),
            result['total'].get('Total', 0)
        ]
        print_table(total_headers, [total_row])
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
        daily_headers.extend(["完了数", "消化数", "計画数"])
        
        daily_rows = []
        for date in sorted(result['daily'].keys()):
            row = [date]
            for rt in result_types:
                count = result['daily'][date].get(rt, 0)
                row.append(count)
            # 完了数、消化数、計画数を追加
            row.append(result['daily'][date].get('完了数', 0))
            row.append(result['daily'][date].get('消化数', 0))
            row.append(result['daily'][date].get('計画数', 0))
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
        name_headers.extend(["完了数", "消化数", "計画数"])
        
        name_rows = []
        for date in sorted(result['by_name'].keys()):
            row = [date]
            for name in names:
                count = result['by_name'][date].get(name, 0)
                row.append(count)
            # 完了数、消化数、計画数を追加
            row.append(result['by_name'][date].get('完了数', 0))
            row.append(result['by_name'][date].get('消化数', 0))
            row.append(result['by_name'][date].get('計画数', 0))
            name_rows.append(row)
        
        print_table(name_headers, name_rows)
        print()
    
    # 環境別集計
    if result['by_env']:
        print("BY ENVIRONMENT:")
        env_headers = ["Date", "Environment"]
        # 結果タイプを取得
        result_types = set()
        for date_data in result['by_env'].values():
            if isinstance(date_data, dict):
                for env_data in date_data.values():
                    if isinstance(env_data, dict):
                        for key, value in env_data.items():
                            if key not in ['完了数', '消化数', '計画数'] and isinstance(value, (int, float)):
                                result_types.add(key)
        result_types = sorted(result_types)
        env_headers.extend(result_types)
        env_headers.extend(["完了数", "消化数", "計画数"])
        
        env_rows = []
        for date in sorted(result['by_env'].keys()):
            date_data = result['by_env'][date]
            if isinstance(date_data, dict):
                for env_name in sorted(date_data.keys()):
                    row = [date, env_name]
                    env_data = date_data[env_name]
                    if isinstance(env_data, dict):
                        for rt in result_types:
                            count = env_data.get(rt, 0)
                            if isinstance(count, (int, float)):
                                row.append(count)
                            else:
                                row.append(0)
                        # 完了数、消化数、計画数を追加
                        row.append(env_data.get('完了数', 0))
                        row.append(env_data.get('消化数', 0))
                        row.append(env_data.get('計画数', 0))
                        env_rows.append(row)
        
        if env_rows:
            print_table(env_headers, env_rows)
            print()

def print_summary_statistics(results):
    # 各ファイルのstatsを集める
    metrics = ["all", "available", "executed", "completed", "incompleted", "planned"]
    stats_list = [r[1]["stats"] for r in results if "stats" in r[1]]
    summary = {}
    for m in metrics:
        values = [s[m] for s in stats_list]
        summary[m] = {
            "total": sum(values)
        }
    # テーブル出力
    headers = ["Metric", "Total"]
    rows = []
    label_map = {
        "all": "All Cases",
        "available": "Available",
        "executed": "Executed",
        "completed": "Completed",
        "incompleted": "Incompleted",
        "planned": "Planned"
    }
    for m in metrics:
        rows.append([
            label_map[m],
            summary[m]["total"]
        ])
    print("SUMMARY STATISTICS:")
    print_table(headers, rows)
    print()

def print_summary_overall(results):
    # ステータス集計
    statuses = [r[1]["run"]["status"] for r in results if "run" in r[1] and r[1]["run"]["status"]]
    if statuses:
        if all(s == "完了" for s in statuses):
            overall_status = "Completed"
        elif any(s == "進行中" for s in statuses):
            overall_status = "In Progress"
        else:
            overall_status = statuses[0]
    else:
        overall_status = "-"
    # 日付集計
    start_dates = [r[1]["run"]["start_date"] for r in results if "run" in r[1] and r[1]["run"]["start_date"]]
    last_updates = [r[1]["run"]["last_update"] for r in results if "run" in r[1] and r[1]["run"]["last_update"]]
    earliest_start = min(start_dates) if start_dates else "-"
    latest_update = max(last_updates) if last_updates else "-"
    print(f"OVERALL STATUS: {overall_status}")
    print(f"Earliest Start Date: {earliest_start}")
    print(f"Latest Update: {latest_update}")
    print()

def parse_args():
    parser = argparse.ArgumentParser(description="TestSpecAnalyticsCLI: Excelテスト集計ツール")
    parser.add_argument("path", help="集計対象のファイルまたはフォルダのパス（.xlsx または ディレクトリ）")
    parser.add_argument("-c", "--config", default="config.json", help="設定ファイルのパス（デフォルト: config.json）")
    parser.add_argument("-f", "--output-format", choices=["table", "json"], default="table", help="出力形式（table/json）")
    parser.add_argument("-j", "--json-output", action="store_true", help="JSON形式で出力")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ出力")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    with open(args.config, encoding="utf-8") as f:
        settings = json.load(f)

    target_path = args.path
    results = []
    file_list = []
    if os.path.isdir(target_path):
        # ディレクトリ配下の全xlsxファイル
        file_list = glob.glob(os.path.join(target_path, "*.xlsx"))
    else:
        file_list = [target_path]

    for filepath in file_list:
        result = ReadData.aggregate_results(filepath, settings)
        results.append((filepath, result))

    # サマリー出力（複数ファイル時）
    if len(file_list) > 1:
        if args.output_format == "json" or args.json_output:
            import json
            # 複数ファイルのJSON出力
            summary_data = {
                "summary": {
                    "processed_files": len(file_list),
                    "processing_time": 0,  # TODO: 処理時間を計測
                    "total_stats": {},
                    "overall_status": "",
                    "earliest_start_date": "",
                    "latest_update": ""
                },
                "files": []
            }
            
            # サマリー統計を計算
            metrics = ["all", "available", "executed", "completed", "incompleted", "planned"]
            stats_list = [r[1]["stats"] for r in results if "stats" in r[1]]
            for m in metrics:
                values = [s[m] for s in stats_list]
                summary_data["summary"]["total_stats"][m] = sum(values)
            
            # 全体ステータスを計算
            statuses = [r[1]["run"]["status"] for r in results if "run" in r[1] and r[1]["run"]["status"]]
            if statuses:
                if all(s == "完了" for s in statuses):
                    summary_data["summary"]["overall_status"] = "completed"
                elif any(s == "進行中" for s in statuses):
                    summary_data["summary"]["overall_status"] = "in_progress"
                else:
                    summary_data["summary"]["overall_status"] = statuses[0]
            
            # 日付を計算
            start_dates = [r[1]["run"]["start_date"] for r in results if "run" in r[1] and r[1]["run"]["start_date"]]
            last_updates = [r[1]["run"]["last_update"] for r in results if "run" in r[1] and r[1]["run"]["last_update"]]
            summary_data["summary"]["earliest_start_date"] = min(start_dates) if start_dates else ""
            summary_data["summary"]["latest_update"] = max(last_updates) if last_updates else ""
            
            # 各ファイルのデータを追加
            for filepath, result in results:
                file_data = result.copy()
                file_data["file"] = filepath
                summary_data["files"].append(file_data)
            
            print(json.dumps(summary_data, ensure_ascii=False, indent=2))
        else:
            print("=" * 50)
            print("TestSpecAnalytics Results")
            print("=" * 50)
            print(f"Processed Files: {len(file_list)}")
            # サマリー統計
            print_summary_statistics(results)
            print_summary_overall(results)
            print()
            for filepath, result in results:
                print("=" * 50)
                format_output(result, filepath, show_title=False)
    else:
        filepath, result = results[0]
        if args.output_format == "json" or args.json_output:
            import json
            # ファイル名を追加
            result["file"] = filepath
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            format_output(result, filepath) 