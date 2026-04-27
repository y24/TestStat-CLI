import json
from utils import ReadData
from utils import Logger
from utils.OutputWriter import OutputWriter
from utils.ClipboardWriter import ClipboardWriter
import sys
import unicodedata
import argparse
import os
import glob
import traceback
from datetime import datetime

# YAMLライブラリのインポート（オプション）
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

def update_project_list_last_loaded(list_file_path):
    """プロジェクトリストファイルのlast_loaded値を現在時刻に更新する"""
    try:
        file_extension = os.path.splitext(list_file_path)[1].lower()
        
        # ファイルを読み込み
        if file_extension in ['.yaml', '.yml']:
            if not YAML_AVAILABLE:
                print(f"WARNING: YAMLファイルの更新に失敗しました。PyYAMLライブラリが必要です: {list_file_path}")
                return False
            with open(list_file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        else:
            print(f"WARNING: サポートされていないファイル形式です: {file_extension} (対応形式: .yaml, .yml)")
            return False
        
        # last_loaded値を現在時刻に更新
        if data and "project" in data:
            data["project"]["last_loaded"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # ファイルに書き戻し
            with open(list_file_path, 'w', encoding='utf-8') as f:
                if file_extension in ['.yaml', '.yml']:
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
    try:
        if not YAML_AVAILABLE:
            raise ImportError("YAMLファイルを処理するにはPyYAMLライブラリが必要です。pip install PyYAML でインストールしてください。")
        
        with open(list_file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"プロジェクトリストファイルが見つかりません: {list_file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"YAMLファイルの形式が不正です: {list_file_path}, 詳細: {e}")
    except Exception as e:
        raise Exception(f"プロジェクトリストファイルの読み込みに失敗しました: {list_file_path}, 詳細: {e}")
    
    # データ構造の検証
    if not isinstance(data, dict):
        raise ValueError(f"プロジェクトリストファイルの形式が不正です: ルート要素が辞書ではありません")
    
    if "project" not in data:
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
        
        if "path" not in file_info:
            raise ValueError(f"プロジェクトリストファイルの形式が不正です: files[{i}]に'path'キーが見つかりません")
        
        if "identifier" not in file_info:
            raise ValueError(f"プロジェクトリストファイルの形式が不正です: files[{i}]に'identifier'キーが見つかりません")
        
        file_path = file_info["path"]
        identifier = file_info["identifier"]
        
        # パスの正規化
        file_path = os.path.normpath(file_path)
        
        file_info_list.append({
            "path": file_path,
            "identifier": identifier
        })
    
    if not file_info_list:
        raise ValueError(f"プロジェクトリストファイルに有効なファイルが含まれていません: {list_file_path}")
    
    return {
        "project_name": project_data["project_name"],
        "files": file_info_list,
        "last_loaded": project_data.get("last_loaded", "")
    }


def read_paths_from_list_file(list_file_path):
    """リストファイルからパスを読み取る（従来の互換性のため残す）"""
    project_data = read_project_list_file(list_file_path)
    return [file_info["path"] for file_info in project_data["files"]]

def get_script_root_dir():
    """スクリプトのルートディレクトリのパスを返す"""
    return os.path.dirname(os.path.abspath(__file__))

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
            script_dir = get_script_root_dir()
            logo_path = os.path.join(script_dir, "assets", "logo.txt")
            with open(logo_path, "r", encoding="utf-8") as f:
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
        total_headers = result_order + ["未実施", "Total", "完了数", "消化数", "完了率(%)", "消化率(%)"]
        total_row = []
        for rt in result_order:
            total_row.append(result['total'].get(rt, 0))
        total_row.extend([
            result['total'].get('未実施', 0),
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
        daily_headers.extend(["完了数", "消化数"])
        # use_plan_rowがtrueの場合のみ計画数を追加
        use_plan_row = settings.get("output_definition", {}).get("use_plan_row", False) if settings else False
        if use_plan_row:
            daily_headers.append("計画数")
        
        daily_rows = []
        for date in sorted(result['daily'].keys()):
            row = [date]
            for rt in result_order:
                count = result['daily'][date].get(rt, 0)
                row.append(count)
            # 完了数、消化数を追加
            row.append(result['daily'][date].get('完了数', 0))
            row.append(result['daily'][date].get('消化数', 0))
            # use_plan_rowがtrueの場合のみ計画数を追加
            if use_plan_row:
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
        
        name_rows = []
        for date in sorted(result['by_name'].keys()):
            row = [date]
            for name in sorted(all_names):
                count = result['by_name'][date].get(name, 0)
                row.append(count)
            name_rows.append(row)
        print_table(name_headers, name_rows)
        print()
    
    # 環境別集計
    if result['by_env']:
        print("BY ENVIRONMENT:")
        # use_plan_rowがtrueの場合のみ計画数を追加
        use_plan_row = settings.get("output_definition", {}).get("use_plan_row", False) if settings else False
        for env_name in sorted(result['by_env'].keys()):
            print(f"\n{env_name}:")
            env_headers = ["Date"]
            env_headers.extend(result_order)
            env_headers.extend(["完了数", "消化数"])
            if use_plan_row:
                env_headers.append("計画数")

            env_rows = []
            # 各環境の全日付を昇順で取得
            dates = sorted(result['by_env'][env_name].keys())
            for date in dates:
                row = [date]
                for rt in result_order:
                    count = result['by_env'][env_name][date].get(rt, 0)
                    row.append(count)
                # 完了数、消化数を追加
                row.append(result['by_env'][env_name][date].get('完了数', 0))
                row.append(result['by_env'][env_name][date].get('消化数', 0))
                # use_plan_rowがtrueの場合のみ計画数を追加
                if use_plan_row:
                    row.append(result['by_env'][env_name][date].get('計画数', 0))
                env_rows.append(row)
            print_table(env_headers, env_rows)
        print()

def print_summary_total_results(results, settings=None):
    """複数ファイルの総合結果を表示"""
    # 各ファイルのtotal_resultsを統合
    total_results = {}
    result_order = settings["test_status"]["results"] if settings else ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
    
    # 初期化
    for rt in result_order:
        total_results[rt] = 0
    total_results["未実施"] = 0
    total_results["Total"] = 0
    total_results["完了数"] = 0
    total_results["消化数"] = 0
    
    # 各ファイルの結果を集計
    for filepath, result in results:
        if "total" in result:
            for rt in result_order:
                total_results[rt] += result["total"].get(rt, 0)
            total_results["未実施"] += result["total"].get("未実施", 0)
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
    total_headers = result_order + ["未実施", "Total", "完了数", "消化数", "完了率(%)", "消化率(%)"]
    total_row = []
    for rt in result_order:
        total_row.append(total_results.get(rt, 0))
    total_row.extend([
        total_results.get("未実施", 0),
        total_results.get("Total", 0),
        total_results.get("完了数", 0),
        total_results.get("消化数", 0),
        total_results.get("完了率(%)", 0),
        total_results.get("消化率(%)", 0)
    ])
    print_table(total_headers, [total_row])
    print()

# ファイル名を省略表示する関数
def shorten_filename(filename, max_width=30):
    """ファイル名が長い場合、先頭と末尾を残して中央を...で省略する（全角半角幅考慮）"""
    if get_display_width(filename) <= max_width:
        return filename
    # 省略記号の幅
    ellipsis = '...'
    ellipsis_width = get_display_width(ellipsis)
    # 先頭・末尾に残す幅を計算
    remain_width = max_width - ellipsis_width
    head_width = remain_width // 2
    tail_width = remain_width - head_width
    # 先頭部分
    head = ''
    w = 0
    for ch in filename:
        ch_w = get_display_width(ch)
        if w + ch_w > head_width:
            break
        head += ch
        w += ch_w
    # 末尾部分
    tail = ''
    w = 0
    for ch in reversed(filename):
        ch_w = get_display_width(ch)
        if w + ch_w > tail_width:
            break
        tail = ch + tail
        w += ch_w
    return head + ellipsis + tail

def print_summary_file_breakdown(results):
    """ファイルごとの簡単な内訳を表示"""
    print("FILE BREAKDOWN:")
    headers = ["File Name", "Available Cases", "Completed", "Completion Rate(%)", "Executed", "Execution Rate(%)"]
    
    rows = []
    for filepath, result in results:
        display_name = shorten_filename(os.path.basename(filepath), 30)
        if "error" in result:
            # エラーの場合はファイル名のみ表示
            rows.append([display_name, "ERROR", "-", "-", "-", "-"])
            continue
        
        if "stats" not in result or "total" not in result:
            rows.append([display_name, "N/A", "-", "-", "-", "-"])
            continue
        
        available = result["stats"]["available"]
        completed = result["total"].get("完了数", 0)
        executed = result["total"].get("消化数", 0)
        
        # 完了率と消化率を計算
        completion_rate = round((completed / available * 100), 2) if available > 0 else 0
        execution_rate = round((executed / available * 100), 2) if available > 0 else 0
        
        rows.append([
            display_name,
            available,
            completed,
            completion_rate,
            executed,
            execution_rate
        ])
    
    print_table(headers, rows)
    print()

def print_summary_errors(results):
    """エラーが発生したファイルの一覧を表示（エラーメッセージ付き）"""
    error_files = []
    for filepath, result in results:
        if "error" in result:
            error_files.append((os.path.basename(filepath), result["error"].get("message", ""), result["error"].get("details", "")))
    
    if error_files:
        print("ERROR SUMMARY:")
        print(f"Files with errors: {len(error_files)}")
        for filename, message, details in error_files:
            print(f"  - {filename}")
            if message:
                print(f"    {message}")
            if details:
                print(f"    ({details})")
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
    # スクリプトのルートディレクトリを取得
    script_dir = get_script_root_dir()
    default_config_path = os.path.join(script_dir, "config.json")
    
    # ヘルプ表示時のみロゴを表示
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        try:
            logo_path = os.path.join(script_dir, "assets", "logo.txt")
            with open(logo_path, "r", encoding="utf-8") as f:
                logo = f.read()
                print(logo)
                print()
        except FileNotFoundError:
            pass
    
    parser = argparse.ArgumentParser(description="Excelテスト仕様書集計ツール")
    parser.add_argument("path", nargs='*', help="集計対象のファイルまたはフォルダのパス（.xlsx または ディレクトリ）。複数指定可能")
    parser.add_argument("-c", "--config", default=default_config_path, help="設定ファイルのパス（デフォルト: ルートフォルダのconfig.json）")
    parser.add_argument("-f", "--output-format", choices=["table", "json", "csv"], default="table", help="出力形式（table/json/csv）")
    parser.add_argument("-o", "--output-file", help="出力ファイルパス")
    parser.add_argument("-j", "--json-output", action="store_true", help="JSON形式で出力")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ出力")
    parser.add_argument("-l", "--list", help="パスリストファイルのパス（YAML形式）")
    
    # TSVクリップボード出力オプション
    parser.add_argument("-p", "--clipboard", action="store_true", help="TSV形式でクリップボードにコピー")
    
    
    # 詳細出力オプション
    parser.add_argument("--detailed", action="store_true", 
                       help="複数ファイル処理時にファイル別の詳細結果も表示")
    
    return parser.parse_args()

def main():
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
    
    # プロジェクトリストファイルまたはターゲットパスの処理
    project_info = None
    if args.list:
        # プロジェクトリストファイルから情報を読み取る
        try:
            project_info = read_project_list_file(args.list)
            if not project_info["files"]:
                print(f"ERROR: プロジェクトリストファイルに有効なファイルが含まれていません: {args.list}")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        
        # 各パスからExcelファイルを検索
        file_list = []
        file_identifiers = {}  # ファイルパスとidentifierのマッピング
        
        for file_info in project_info["files"]:
            target_path = file_info["path"]
            identifier = file_info["identifier"]
            
            if not os.path.exists(target_path):
                print(f"WARNING: 指定されたパスが存在しません: {target_path}")
                continue
            
            is_valid, file_list_or_error = find_excel_files(target_path)
            if not is_valid:
                print(f"WARNING: {file_list_or_error}")
                continue
            
            if isinstance(file_list_or_error, list):
                file_list.extend(file_list_or_error)
                # 各ファイルにidentifierを関連付け
                for file_path in file_list_or_error:
                    file_identifiers[file_path] = identifier
        
        if not file_list:
            print("ERROR: 処理可能なファイルが見つかりませんでした")
            sys.exit(1)
    else:
        # 複数パス処理
        if not args.path:
            print("ERROR: パスまたはプロジェクトリストファイルを指定してください")
            sys.exit(1)
        
        # 各パスからExcelファイルを検索
        file_list = []
        file_identifiers = {}  # 複数パス処理ではidentifierは空
        
        for target_path in args.path:
            if not os.path.exists(target_path):
                print(f"WARNING: 指定されたパスが存在しません: {target_path}")
                continue
            
            # Excelファイルの検索
            is_valid, file_list_or_error = find_excel_files(target_path)
            if not is_valid:
                print(f"WARNING: {file_list_or_error}")
                continue
            
            if isinstance(file_list_or_error, list):
                file_list.extend(file_list_or_error)
        
        if not file_list:
            print("ERROR: 処理可能なファイルが見つかりませんでした")
            sys.exit(1)
    
    # ファイル検索結果をログ出力
    if args.list:
        verbose_logger.log_file_search(args.list, len(file_list))
    else:
        verbose_logger.log_file_search(f"{len(args.path)} paths", len(file_list))
    
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
            
            # identifierを結果に追加
            if filepath in file_identifiers:
                result["identifier"] = file_identifiers[filepath]
            
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

    # 出力データの準備
    if len(file_list) > 1:
        # 複数ファイル処理
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
        
        # TOTAL RESULTSの統合計算
        total_results = {
            "Pass": 0, "Fixed": 0, "Fail": 0, "Blocked": 0, "Suspend": 0, "N/A": 0,
            "未実施": 0, "Total": 0, "完了数": 0, "消化数": 0, "完了率(%)": 0, "消化率(%)": 0
        }
        
        for filepath, result in results:
            if "total" in result:
                for key, value in result["total"].items():
                    if key in total_results and isinstance(value, (int, float)):
                        total_results[key] += value
        
        # 完了率・消化率の再計算
        if total_results["消化数"] > 0:
            total_results["完了率(%)"] = round(total_results["完了数"] / total_results["消化数"] * 100, 2)
        if summary_data["summary"]["total_stats"]["available"] > 0:
            total_results["消化率(%)"] = round(total_results["消化数"] / summary_data["summary"]["total_stats"]["available"] * 100, 2)
        
        summary_data["summary"]["total_results"] = total_results
        
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
        
        output_data = summary_data
        is_multiple_files = True
    else:
        # 単一ファイル処理
        filepath, result = results[0]
        result["file"] = filepath
        
        
        output_data = result
        is_multiple_files = False
    
    # ファイル出力処理
    if args.output_file:
        output_writer = OutputWriter(verbose_logger)
        
        output_file = args.output_file
        
        # 出力形式の決定
        if args.output_format == "csv":
            output_format = "csv"
        elif args.output_file.endswith('.csv'):
            output_format = "csv"
        else:
            # デフォルトはCSV
            output_format = "csv"
            if not output_file.endswith('.csv'):
                output_file = output_file + '.csv'
        
        # ファイル拡張子の検証
        if output_format == "csv" and not output_file.endswith('.csv'):
            print(f"ERROR: CSV出力には.csv拡張子が必要です: {output_file}")
            sys.exit(1)
        
        # ファイル出力実行
        if output_format == "csv":
            success, error = output_writer.write_csv(output_data, output_file, is_multiple_files, settings)
        else:
            success, error = False, f"サポートされていない出力形式です: {output_format}"
        
        if not success:
            print(f"ERROR: {error}")
            sys.exit(1)
        
        # ファイル出力時はコンソール出力を抑制
        if args.output_format == "csv":
            sys.exit(0)
    
    # TSVクリップボード出力処理
    clipboard_writer = ClipboardWriter(verbose_logger)
    
    if args.clipboard:
        # クリップボード用のデータを準備
        clipboard_data = []
        if is_multiple_files:
            # 複数ファイル処理の場合、各ファイルのデータをリストに追加
            for filepath, result in results:
                result["file"] = filepath
                clipboard_data.append(result)
        else:
            # 単一ファイル処理の場合
            filepath, result = results[0]
            result["file"] = filepath
            clipboard_data.append(result)
        
        # クリップボードにコピー
        success = clipboard_writer.write_to_clipboard(clipboard_data, settings)
        
        if not success:
            print("ERROR: クリップボードへのコピーに失敗しました")
            sys.exit(1)
    
    # コンソール出力処理
    if args.output_format == "json" or args.json_output:
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
    else:
        # テーブル形式出力
        if len(file_list) > 1:
            # ロゴを表示
            try:
                script_dir = get_script_root_dir()
                logo_path = os.path.join(script_dir, "assets", "logo.txt")
                with open(logo_path, "r", encoding="utf-8") as f:
                    logo = f.read()
                    print(logo)
            except FileNotFoundError:
                pass
            print()
            print("=" * 50)
            print("Summary Results")
            print("=" * 50)
            # --- ここでプロジェクト名等を出力 ---
            if args.list and project_info:
                print(f"Project: {project_info['project_name']}")
                print(f"Processed Files: {len(file_list)}")
                if project_info.get('last_loaded'):
                    print(f"Last Loaded: {project_info['last_loaded']}")
                print()
            # --- ここまで追加 ---
            if args.list:
                print(f"List File: {args.list}")
            else:
                print(f"Input Paths: {len(args.path)}")
                for i, path in enumerate(args.path, 1):
                    print(f"  {i}. {path}")
                print()
            print(f"Processed Files: {len(file_list)}")
            # サマリー総合結果
            print_summary_total_results(results, settings)
            print_summary_file_breakdown(results)
            print_summary_errors(results)
            print_summary_overall(results)
            
            # 詳細出力オプションが指定されている場合のみファイル別の結果を表示
            if args.detailed:
                print()
                for filepath, result in results:
                    print("=" * 50)
                    format_output(result, filepath, show_title=False, settings=settings)
        else:
            filepath, result = results[0]
            format_output(result, filepath, settings=settings)
    
    # プロジェクトリストファイルのlast_loaded値を更新
    if args.list:
        update_success = update_project_list_last_loaded(args.list)
        if update_success and verbose_logger:
            verbose_logger.log(f"プロジェクトリストファイルのlast_loaded値を更新しました: {args.list}")
    
    # 全体処理終了
    verbose_logger.end_processing()

if __name__ == "__main__":
    main() 