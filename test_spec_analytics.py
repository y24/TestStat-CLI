import json
from utils import ReadData
import sys
import unicodedata
import argparse
import os
import glob
import traceback

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

def validate_config(config_data):
    """設定ファイルの妥当性をチェック"""
    required_sections = ["read_definition", "test_status", "output_definition"]
    for section in required_sections:
        if section not in config_data:
            return False, f"設定ファイルに必要なセクション '{section}' がありません"
    
    # read_definition の必須項目チェック
    read_def = config_data["read_definition"]
    required_read_keys = ["sheet_search_keys", "header", "result_row", "person_row", "date_row"]
    for key in required_read_keys:
        if key not in read_def:
            return False, f"read_definition に必要な項目 '{key}' がありません"
    
    # test_status の必須項目チェック
    test_status = config_data["test_status"]
    required_test_keys = ["results", "completed_results", "executed_results"]
    for key in required_test_keys:
        if key not in test_status:
            return False, f"test_status に必要な項目 '{key}' がありません"
    
    return True, "設定ファイルは正常です"

def check_file_access(filepath):
    """ファイルアクセス権限をチェック"""
    if not os.path.exists(filepath):
        return False, f"ファイルが見つかりません: {filepath}"
    
    if not os.access(filepath, os.R_OK):
        return False, f"ファイルの読み取り権限がありません: {filepath}"
    
    return True, "ファイルアクセス可能"

def find_excel_files(target_path):
    """Excelファイルを検索"""
    if os.path.isdir(target_path):
        # ディレクトリ配下の全xlsxファイル
        file_list = glob.glob(os.path.join(target_path, "**/*.xlsx"), recursive=True)
        if not file_list:
            return False, f"指定されたディレクトリにExcelファイルが見つかりません: {target_path}"
    else:
        # 単一ファイル
        if not target_path.lower().endswith('.xlsx'):
            return False, f"指定されたファイルはExcelファイルではありません: {target_path}"
        file_list = [target_path]
    
    return True, file_list

def format_output(result, filepath, show_title=True, settings=None):
    """集計結果を美しいテーブル形式で出力"""
    if show_title:
        # ロゴを表示
        try:
            with open("assets/logo.txt", "r", encoding="utf-8") as f:
                logo = f.read()
                print(logo)
        except FileNotFoundError:
            pass
        print()
        print("=" * 50)
        print("Summary Results")
        print("=" * 50)
        print()
    
    if "error" in result:
        print(f"ERROR: {result['error']['message']}")
        if "details" in result["error"]:
            print(f"詳細: {result['error']['details']}")
        return
    
    # 基本情報
    print(f"File: {filepath}")
    print(f"Total Cases: {result['stats']['all']}")
    print(f"Available Cases: {result['stats']['available']}")
    print(f"Excluded Cases: {result['stats']['excluded']}")
    print()
    
    # 設定から結果タイプの順序を取得
    result_order = settings["test_status"]["results"] if settings else ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
    
    # 総合結果テーブル
    if 'total' in result:
        print("TOTAL RESULTS:")
        total_headers = result_order + ["Total", "完了数", "消化数", "完了率(%)", "消化率(%)"]
        total_row = []
        for rt in result_order:
            total_row.append(result['total'].get(rt, 0))
        total_row.extend([
            result['total'].get('Total', 0),
            result['total'].get('完了数', 0),
            result['total'].get('消化数', 0),
            result['total'].get('完了率(%)', 0),
            result['total'].get('消化率(%)', 0)
        ])
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
        # 設定の結果タイプ順序を使用
        daily_headers.extend(result_order)
        daily_headers.extend(["完了数", "消化数", "計画数"])
        
        daily_rows = []
        for date in sorted(result['daily'].keys()):
            row = [date]
            for rt in result_order:
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
        # 設定の結果タイプ順序を使用
        env_headers.extend(result_order)
        env_headers.extend(["完了数", "消化数", "計画数"])
        
        env_rows = []
        for date in sorted(result['by_env'].keys()):
            date_data = result['by_env'][date]
            if isinstance(date_data, dict):
                for env_name in sorted(date_data.keys()):
                    row = [date, env_name]
                    env_data = date_data[env_name]
                    if isinstance(env_data, dict):
                        for rt in result_order:
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

def print_summary_total_results(results, settings=None):
    """複数ファイルのTOTAL RESULTSを集計して表示"""
    # 各ファイルのtotal_resultsを集める
    total_results_list = [r[1]["total"] for r in results if "total" in r[1]]
    
    if not total_results_list:
        return
    
    # 集計用の変数を初期化
    combined_total = {}
    
    # 各ファイルの結果を統合
    for total_result in total_results_list:
        for result_type, count in total_result.items():
            if result_type not in ["Total", "完了数", "消化数"]:  # Total、完了数、消化数は後で計算
                combined_total[result_type] = combined_total.get(result_type, 0) + count
    
    # Totalを計算
    combined_total["Total"] = sum(combined_total.values())
    
    # 完了数と消化数を各ファイルのdailyデータから集計
    completed_count = 0
    executed_count = 0
    
    for filepath, result in results:
        if "daily" in result:
            for date_data in result["daily"].values():
                # 完了数（completed_resultsに含まれる結果の合計）
                completed_count += date_data.get("完了数", 0)
                # 消化数（executed_resultsに含まれる結果の合計）
                executed_count += date_data.get("消化数", 0)
    
    # 完了率と消化率を計算
    # 各ファイルのstatsからavailable_countを集計
    available_count = 0
    for filepath, result in results:
        if "stats" in result and "available" in result["stats"]:
            available_count += result["stats"]["available"]
    
    completion_rate = (completed_count / available_count * 100) if available_count > 0 else 0
    execution_rate = (executed_count / available_count * 100) if available_count > 0 else 0
    
    # 完了数と消化数を追加
    combined_total["完了数"] = completed_count
    combined_total["消化数"] = executed_count
    combined_total["完了率(%)"] = round(completion_rate, 2)
    combined_total["消化率(%)"] = round(execution_rate, 2)
    
    # 設定から結果タイプの順序を取得
    result_order = settings["test_status"]["results"] if settings else ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
    
    # テーブル出力
    headers = result_order + ["Total", "完了数", "消化数", "完了率(%)", "消化率(%)"]
    row = []
    for rt in result_order:
        row.append(combined_total.get(rt, 0))
    row.extend([
        combined_total.get("Total", 0),
        combined_total.get("完了数", 0),
        combined_total.get("消化数", 0),
        combined_total.get("完了率(%)", 0),
        combined_total.get("消化率(%)", 0)
    ])
    print("SUMMARY TOTAL RESULTS:")
    print_table(headers, [row])
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
    # ロゴを表示
    try:
        with open("assets/logo.txt", "r", encoding="utf-8") as f:
            logo = f.read()
            print(logo)
            print()
    except FileNotFoundError:
        pass
    
    parser = argparse.ArgumentParser(description="TestSpecAnalyticsCLI: Excelテスト集計ツール")
    parser.add_argument("path", help="集計対象のファイルまたはフォルダのパス（.xlsx または ディレクトリ）")
    parser.add_argument("-c", "--config", default="config.json", help="設定ファイルのパス（デフォルト: config.json）")
    parser.add_argument("-f", "--output-format", choices=["table", "json"], default="table", help="出力形式（table/json）")
    parser.add_argument("-j", "--json-output", action="store_true", help="JSON形式で出力")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ出力")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # 設定ファイルの読み込みと検証
    try:
        with open(args.config, encoding="utf-8") as f:
            settings = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: 設定ファイルが見つかりません: {args.config}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: 設定ファイルのJSON形式が不正です: {args.config}")
        print(f"詳細: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: 設定ファイルの読み込みに失敗しました: {args.config}")
        print(f"詳細: {e}")
        sys.exit(1)
    
    # 設定ファイルの妥当性チェック
    is_valid, message = validate_config(settings)
    if not is_valid:
        print(f"ERROR: {message}")
        sys.exit(1)
    
    # ターゲットパスの検証
    target_path = args.path
    if not os.path.exists(target_path):
        print(f"ERROR: 指定されたパスが存在しません: {target_path}")
        sys.exit(1)
    
    # Excelファイルの検索
    is_valid, file_list_or_error = find_excel_files(target_path)
    if not is_valid:
        print(f"ERROR: {file_list_or_error}")
        sys.exit(1)
    
    file_list = file_list_or_error
    results = []
    
    # 各ファイルの処理
    for filepath in file_list:
        # ファイルアクセス権限チェック
        is_accessible, message = check_file_access(filepath)
        if not is_accessible:
            print(f"WARNING: {message}")
            continue
        
        try:
            result = ReadData.aggregate_results(filepath, settings)
            results.append((filepath, result))
        except Exception as e:
            error_result = {
                "error": {
                    "type": "processing_error",
                    "message": f"ファイル処理中にエラーが発生しました: {filepath}",
                    "details": str(e)
                }
            }
            if args.verbose:
                print(f"詳細エラー情報: {traceback.format_exc()}")
            results.append((filepath, error_result))
    
    # 処理対象ファイルが存在しない場合
    if not results:
        print("ERROR: 処理可能なファイルが見つかりませんでした")
        sys.exit(1)

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
            # ロゴを表示
            try:
                with open("assets/logo.txt", "r", encoding="utf-8") as f:
                    logo = f.read()
                    print(logo)
            except FileNotFoundError:
                pass
            print("=" * 50)
            print("TestSpecAnalytics Results")
            print("=" * 50)
            print(f"Processed Files: {len(file_list)}")
            # サマリー総合結果
            print_summary_total_results(results, settings)
            # サマリー統計
            print_summary_statistics(results)
            print_summary_overall(results)
            print()
            for filepath, result in results:
                print("=" * 50)
                format_output(result, filepath, show_title=False, settings=settings)
    else:
        filepath, result = results[0]
        if args.output_format == "json" or args.json_output:
            import json
            # ファイル名を追加
            result["file"] = filepath
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            format_output(result, filepath, settings=settings) 