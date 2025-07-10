import json
from utils import ReadData
from utils import Logger
import sys
import unicodedata
import argparse
import os
import glob
import traceback

def read_paths_from_list_file(list_file_path):
    """リストファイルからパスを読み取る"""
    paths = []
    try:
        with open(list_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):  # 空行とコメント行をスキップ
                    continue
                
                # ダブルクォーテーションで囲まれたパスを処理
                if line.startswith('"') and line.endswith('"'):
                    path = line[1:-1]  # ダブルクォーテーションを除去
                else:
                    path = line
                
                # パスの正規化
                path = os.path.normpath(path)
                paths.append(path)
                
    except FileNotFoundError:
        raise FileNotFoundError(f"リストファイルが見つかりません: {list_file_path}")
    except Exception as e:
        raise Exception(f"リストファイルの読み込みに失敗しました: {list_file_path}, 詳細: {e}")
    
    return paths

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
        all_names = set()
        for date_data in result['by_name'].values():
            all_names.update(date_data.keys())
        name_headers.extend(sorted(all_names))
        name_headers.extend(["完了数", "消化数", "計画数"])
        
        name_rows = []
        for date in sorted(result['by_name'].keys()):
            row = [date]
            for name in sorted(all_names):
                count = result['by_name'][date].get(name, 0)
                row.append(count)
            # 完了数、消化数、計画数を追加（日別データから取得）
            daily_data = result['daily'].get(date, {})
            row.append(daily_data.get('完了数', 0))
            row.append(daily_data.get('消化数', 0))
            row.append(daily_data.get('計画数', 0))
            name_rows.append(row)
        print_table(name_headers, name_rows)
        print()
    
    # 環境別集計
    if result['by_env']:
        print("BY ENVIRONMENT:")
        for env_name in sorted(result['by_env'].keys()):
            print(f"\n{env_name}:")
            env_headers = ["Date"]
            env_headers.extend(result_order)
            env_headers.extend(["完了数", "消化数", "計画数"])
            
            env_rows = []
            for date in sorted(result['by_env'][env_name].keys()):
                row = [date]
                for rt in result_order:
                    count = result['by_env'][env_name][date].get(rt, 0)
                    row.append(count)
                # 完了数、消化数、計画数を追加
                row.append(result['by_env'][env_name][date].get('完了数', 0))
                row.append(result['by_env'][env_name][date].get('消化数', 0))
                row.append(result['by_env'][env_name][date].get('計画数', 0))
                env_rows.append(row)
            print_table(env_headers, env_rows)

def print_summary_total_results(results, settings=None):
    """複数ファイルの総合結果を表示"""
    # 各ファイルのtotal_resultsを統合
    total_results = {}
    result_order = settings["test_status"]["results"] if settings else ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
    
    # 初期化
    for rt in result_order:
        total_results[rt] = 0
    total_results["Total"] = 0
    total_results["完了数"] = 0
    total_results["消化数"] = 0
    
    # 各ファイルの結果を集計
    for filepath, result in results:
        if "total" in result:
            for rt in result_order:
                total_results[rt] += result["total"].get(rt, 0)
            total_results["Total"] += result["total"].get("Total", 0)
            total_results["完了数"] += result["total"].get("完了数", 0)
            total_results["消化数"] += result["total"].get("消化数", 0)
    
    # 完了率と消化率を計算
    total_available = sum(r[1]["stats"]["available"] for r in results if "stats" in r[1])
    completion_rate = (total_results["完了数"] / total_available * 100) if total_available > 0 else 0
    execution_rate = (total_results["消化数"] / total_available * 100) if total_available > 0 else 0
    
    total_results["完了率(%)"] = round(completion_rate, 2)
    total_results["消化率(%)"] = round(execution_rate, 2)
    
    print("SUMMARY TOTAL RESULTS:")
    total_headers = result_order + ["Total", "完了数", "消化数", "完了率(%)", "消化率(%)"]
    total_row = []
    for rt in result_order:
        total_row.append(total_results.get(rt, 0))
    total_row.extend([
        total_results.get("Total", 0),
        total_results.get("完了数", 0),
        total_results.get("消化数", 0),
        total_results.get("完了率(%)", 0),
        total_results.get("消化率(%)", 0)
    ])
    print_table(total_headers, [total_row])
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
        overall_status = "Unknown"
    
    # 日付を計算
    start_dates = [r[1]["run"]["start_date"] for r in results if "run" in r[1] and r[1]["run"]["start_date"]]
    last_updates = [r[1]["run"]["last_update"] for r in results if "run" in r[1] and r[1]["run"]["last_update"]]
    earliest_start = min(start_dates) if start_dates else ""
    latest_update = max(last_updates) if last_updates else ""
    
    print(f"OVERALL STATUS: {overall_status}")
    if earliest_start:
        print(f"Earliest Start Date: {earliest_start}")
    if latest_update:
        print(f"Latest Update: {latest_update}")
    print()

def parse_args():
    # ヘルプ表示時のみロゴを表示
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        try:
            with open("assets/logo.txt", "r", encoding="utf-8") as f:
                logo = f.read()
                print(logo)
                print()
        except FileNotFoundError:
            pass
    
    parser = argparse.ArgumentParser(description="Excelテスト仕様書集計ツール")
    parser.add_argument("path", nargs='?', help="集計対象のファイルまたはフォルダのパス（.xlsx または ディレクトリ）")
    parser.add_argument("-c", "--config", default="config.json", help="設定ファイルのパス（デフォルト: config.json）")
    parser.add_argument("-f", "--output-format", choices=["table", "json"], default="table", help="出力形式（table/json）")
    parser.add_argument("-j", "--json-output", action="store_true", help="JSON形式で出力")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ出力")
    parser.add_argument("-l", "--list", help="パスリストファイルのパス（ファイル内の各行にパスを記述）")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # VerboseLoggerの初期化
    verbose_logger = Logger.VerboseLogger(args.verbose)
    
    # 全体処理開始
    verbose_logger.start_processing()
    
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
    
    # リストファイルまたはターゲットパスの処理
    if args.list:
        # リストファイルからパスを読み取る
        try:
            target_paths = read_paths_from_list_file(args.list)
            if not target_paths:
                print(f"ERROR: リストファイルに有効なパスが含まれていません: {args.list}")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        
        # 各パスからExcelファイルを検索
        file_list = []
        for target_path in target_paths:
            if not os.path.exists(target_path):
                print(f"WARNING: 指定されたパスが存在しません: {target_path}")
                continue
            
            is_valid, file_list_or_error = find_excel_files(target_path)
            if not is_valid:
                print(f"WARNING: {file_list_or_error}")
                continue
            
            if isinstance(file_list_or_error, list):
                file_list.extend(file_list_or_error)
        
        if not file_list:
            print("ERROR: 処理可能なファイルが見つかりませんでした")
            sys.exit(1)
    else:
        # 従来の単一パス処理
        if not args.path:
            print("ERROR: パスまたはリストファイルを指定してください")
            sys.exit(1)
        
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
    
    # ファイル検索結果をログ出力
    verbose_logger.log_file_search(target_path if not args.list else args.list, len(file_list))
    
    results = []
    
    # 各ファイルの処理
    for filepath in file_list:
        # ファイルアクセス権限チェック
        is_accessible, message = check_file_access(filepath)
        if not is_accessible:
            print(f"WARNING: {message}")
            continue
        
        try:
            result = ReadData.aggregate_results(filepath, settings, verbose_logger)
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
            print()
            print("=" * 50)
            print("TestSpecAnalytics Results")
            print("=" * 50)
            if args.list:
                print(f"List File: {args.list}")
            print(f"Processed Files: {len(file_list)}")
            # サマリー総合結果
            print_summary_total_results(results, settings)
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
    
    # 全体処理終了
    verbose_logger.end_processing() 