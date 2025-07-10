import json
from utils import ReadData
from utils import Logger
import sys
import unicodedata
import argparse
import os
import glob
import traceback
from datetime import datetime

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

def validate_date_format(date_str):
    """日付形式の妥当性をチェック"""
    if not date_str:
        return True, None
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, None
    except ValueError:
        return False, f"無効な日付形式です: {date_str} (YYYY-MM-DD形式で指定してください)"

def validate_date_range(start_date, end_date):
    """日付範囲の妥当性をチェック"""
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                return False, f"開始日（{start_date}）が終了日（{end_date}）より後になっています"
        except ValueError:
            return False, "日付形式が無効です"
    return True, None

def validate_result_types(result_types, settings):
    """結果タイプの妥当性をチェック"""
    if not result_types:
        return True, None
    
    valid_types = settings["test_status"]["results"]
    invalid_types = [rt for rt in result_types if rt not in valid_types]
    
    if invalid_types:
        return False, f"無効な結果タイプです: {', '.join(invalid_types)} (有効: {', '.join(valid_types)})"
    
    return True, None

def create_filter_conditions(args, settings):
    """フィルタリング条件を作成"""
    filters = {}
    
    # 日付範囲フィルタ
    if args.date_range:
        start_date = args.date_range[0] if args.date_range else None
        end_date = args.date_range[1] if len(args.date_range) > 1 else None
        
        # 日付形式の妥当性チェック
        if start_date:
            is_valid, error = validate_date_format(start_date)
            if not is_valid:
                raise ValueError(error)
        if end_date:
            is_valid, error = validate_date_format(end_date)
            if not is_valid:
                raise ValueError(error)
        
        # 日付範囲の妥当性チェック
        is_valid, error = validate_date_range(start_date, end_date)
        if not is_valid:
            raise ValueError(error)
        
        filters["date_range"] = {
            "start": start_date,
            "end": end_date
        }
    
    # 担当者フィルタ
    if args.assignee:
        filters["assignee"] = {
            "value": args.assignee.strip(),
            "exact_match": args.exact_match
        }
    
    # 結果タイプフィルタ
    if args.result_type:
        is_valid, error = validate_result_types(args.result_type, settings)
        if not is_valid:
            raise ValueError(error)
        filters["result_type"] = args.result_type
    
    # 環境フィルタ
    if args.environment:
        filters["environment"] = {
            "value": args.environment.strip(),
            "exact_match": args.exact_match
        }
    
    return filters

def format_filter_display(filters):
    """フィルタ条件を表示用にフォーマット"""
    if not filters:
        return None
    
    conditions = []
    
    # 日付範囲
    if "date_range" in filters:
        start = filters["date_range"]["start"]
        end = filters["date_range"]["end"]
        if start and end:
            conditions.append(f"Date Range: {start} to {end}")
        elif start:
            conditions.append(f"Date Range: {start} onwards")
        elif end:
            conditions.append(f"Date Range: up to {end}")
    
    # 担当者
    if "assignee" in filters:
        match_type = "exact match" if filters["assignee"]["exact_match"] else "partial match"
        conditions.append(f"Assignee: {filters['assignee']['value']} ({match_type})")
    
    # 結果タイプ
    if "result_type" in filters:
        if len(filters["result_type"]) == 1:
            conditions.append(f"Result Type: {filters['result_type'][0]}")
        else:
            conditions.append(f"Result Type: {', '.join(filters['result_type'])}")
    
    # 環境
    if "environment" in filters:
        match_type = "exact match" if filters["environment"]["exact_match"] else "partial match"
        conditions.append(f"Environment: {filters['environment']['value']} ({match_type})")
    
    return conditions

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

def format_output(result, filepath, show_title=True, settings=None, filters=None):
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
        print("TestSpecAnalytics Results")
        print("=" * 50)
        print()
    
    if "error" in result:
        print(f"ERROR: {result['error']['message']}")
        if "details" in result["error"]:
            print(f"詳細: {result['error']['details']}")
        return
    
    # フィルタ条件の表示
    if filters:
        filter_conditions = format_filter_display(filters)
        if filter_conditions:
            print("Filter Conditions:")
            for condition in filter_conditions:
                print(f"- {condition}")
            print()
    
    # 基本情報
    print(f"File: {filepath}")
    
    # フィルタ適用後の統計情報
    if filters and "filtered_stats" in result:
        print(f"Filtered Cases: {result['filtered_stats']['filtered_count']} (from {result['stats']['all']} total cases)")
        print(f"Available Cases: {result['stats']['available']}")
        print(f"Excluded Cases: {result['stats']['excluded']}")
    else:
        print(f"Total Cases: {result['stats']['all']}")
        print(f"Available Cases: {result['stats']['available']}")
        print(f"Excluded Cases: {result['stats']['excluded']}")
    print()
    
    # 設定から結果タイプの順序を取得
    result_order = settings["test_status"]["results"] if settings else ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
    
    # 総合結果テーブル
    if 'total' in result:
        # フィルタ適用後の場合は "(Filtered)" を追加
        table_title = "TOTAL RESULTS (Filtered):" if filters else "TOTAL RESULTS:"
        print(table_title)
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
    
    # フィルタリングオプション
    parser.add_argument("--date-range", nargs="*", metavar=("START_DATE", "END_DATE"), 
                       help="日付範囲フィルタ（YYYY-MM-DD形式、終了日は省略可能）")
    parser.add_argument("--assignee", help="担当者フィルタ（部分一致）")
    parser.add_argument("--exact-match", action="store_true", 
                       help="担当者・環境フィルタで完全一致を使用")
    parser.add_argument("--result-type", nargs="+", 
                       help="結果タイプフィルタ（複数指定可能）")
    parser.add_argument("--environment", help="環境フィルタ（部分一致）")
    
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
            # フィルタリング条件を作成
            filters = create_filter_conditions(args, settings)
            result = ReadData.aggregate_results(filepath, settings, verbose_logger, filters)
            results.append((filepath, result))
        except ValueError as e:
            # フィルタリング条件のバリデーションエラー
            print(f"ERROR: {e}")
            sys.exit(1)
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
                
                # フィルタ情報を追加
                filters = create_filter_conditions(args, settings)
                if filters:
                    file_data["filters"] = filters
                    if "filtered_stats" in file_data:
                        file_data["filtered_cases"] = file_data["filtered_stats"]["filtered_count"]
                        file_data["total_cases"] = file_data["filtered_stats"]["original_count"]
                
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
                # フィルタリング条件を表示
                filters = create_filter_conditions(args, settings)
                format_output(result, filepath, show_title=False, settings=settings, filters=filters)
    else:
        filepath, result = results[0]
        if args.output_format == "json" or args.json_output:
            import json
            # ファイル名を追加
            result["file"] = filepath
            
            # フィルタ情報を追加
            filters = create_filter_conditions(args, settings)
            if filters:
                result["filters"] = filters
                if "filtered_stats" in result:
                    result["filtered_cases"] = result["filtered_stats"]["filtered_count"]
                    result["total_cases"] = result["filtered_stats"]["original_count"]
            
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # フィルタリング条件を表示
            filters = create_filter_conditions(args, settings)
            format_output(result, filepath, settings=settings, filters=filters)
    
    # 全体処理終了
    verbose_logger.end_processing() 