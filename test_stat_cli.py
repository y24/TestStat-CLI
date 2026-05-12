import json
import copy
import sys
import argparse
import os
import traceback
from datetime import datetime

from utils import ReadData
from utils import Logger
from utils.OutputWriter import OutputWriter
from utils.ClipboardWriter import ClipboardWriter
from utils import ProjectList
from utils import FileScanner
from utils import ConsoleFormatter

def get_script_root_dir():
    """スクリプトのルートディレクトリのパスを返す"""
    return os.path.dirname(os.path.abspath(__file__))

def get_version(script_dir):
    """pyproject.tomlからバージョン情報を取得する"""
    pyproject_path = os.path.join(script_dir, "pyproject.toml")
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("version"):
                        # 'version = "1.0.0"' の形式から "1.0.0" を抽出
                        return line.split("=")[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return "unknown"

def parse_args():
    # スクリプトのルートディレクトリを取得
    script_dir = get_script_root_dir()
    default_config_path = os.path.join(script_dir, "config.json")
    version = get_version(script_dir)
    
    # ヘルプ表示時のみロゴを表示
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        ConsoleFormatter.print_logo(script_dir)
    
    parser = argparse.ArgumentParser(description=f"Excelテスト仕様書集計ツール (version {version})")
    parser.add_argument("path", nargs='*', help="集計対象のファイルまたはフォルダのパス（.xlsx または ディレクトリ）。複数指定可能")
    parser.add_argument("-c", "--config", default=default_config_path, help="設定ファイルのパス（デフォルト: ルートフォルダのconfig.json）")
    parser.add_argument("-f", "--output-format", choices=["table", "json", "csv"], default="table", help="出力形式（table/json/csv）")
    parser.add_argument("-o", "--output-file", help="出力ファイルパス")
    parser.add_argument("-j", "--json-output", action="store_true", help="JSON形式で出力")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ出力")
    parser.add_argument("-l", "--list", help="パスリストファイルのパス（YAML形式）")
    parser.add_argument("-p", "--clipboard", action="store_true", help="TSV形式でクリップボードにコピー")
    parser.add_argument("--detailed", action="store_true", help="複数ファイル処理時にファイル別の詳細結果も表示")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version}", help="バージョン情報を表示して終了")
    
    return parser.parse_args()

def main():
    args = parse_args()
    script_dir = get_script_root_dir()
    is_json_mode = args.json_output or args.output_format == "json"
    
    # VerboseLoggerの初期化
    verbose_logger = Logger.VerboseLogger(args.verbose)
    verbose_logger.start_processing()
    
    # 設定ファイルの読み込みと検証
    try:
        with open(args.config, encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        print(f"ERROR: 設定ファイルの読み込みに失敗しました: {args.config}\n詳細: {e}", file=sys.stderr)
        sys.exit(1)
    
    is_valid, message = FileScanner.validate_config(settings)
    if not is_valid:
        print(f"ERROR: {message}", file=sys.stderr)
        sys.exit(1)
    
    # ファイルリストの作成
    tasks = []
    project_info = None
    execution_warnings = []

    if args.list:
        try:
            project_info = ProjectList.read_project_list_file(args.list)
            for file_info in project_info["files"]:
                target_path = file_info["path"]
                if not os.path.exists(target_path):
                    execution_warnings.append(f"指定されたパスが存在しません: {target_path}")
                    continue
                
                is_valid_search, found_files = FileScanner.find_excel_files(target_path)
                if is_valid_search:
                    for f in found_files:
                        task = {
                            "filepath": f,
                            "label": file_info.get("label", ""),
                            "overrides": {},
                            "subtask_id": file_info.get("subtask_id")
                        }
                        
                        # 個別設定の保持
                        if "target_sheets" in file_info:
                            task["overrides"]["target_sheets"] = file_info["target_sheets"]
                        if "ignore_sheets" in file_info:
                            task["overrides"]["ignore_sheets"] = file_info["ignore_sheets"]
                        if "include_hidden_sheets" in file_info:
                            task["overrides"]["include_hidden_sheets"] = file_info["include_hidden_sheets"]
                        if "target_environments" in file_info:
                            task["overrides"]["target_environments"] = file_info["target_environments"]
                        if "ignore_environments" in file_info:
                            task["overrides"]["ignore_environments"] = file_info["ignore_environments"]
                            
                        tasks.append(task)
                else:
                    execution_warnings.append(str(found_files))
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.path:
            print("ERROR: パスまたはプロジェクトリストファイルを指定してください", file=sys.stderr)
            sys.exit(1)
        for target_path in args.path:
            if not os.path.exists(target_path):
                execution_warnings.append(f"指定されたパスが存在しません: {target_path}")
                continue
            is_valid_search, found_files = FileScanner.find_excel_files(target_path)
            if is_valid_search:
                for f in found_files:
                    tasks.append({
                        "filepath": f,
                        "label": "",
                        "overrides": {},
                        "subtask_id": None
                    })
            else:
                execution_warnings.append(str(found_files))

    if not tasks:
        if is_json_mode:
            print(json.dumps({"error": "処理可能なファイルが見つかりませんでした", "warnings": execution_warnings}, ensure_ascii=False, indent=2))
        else:
            if execution_warnings:
                print()
                ConsoleFormatter.print_section("Warnings")
                for w in execution_warnings:
                    ConsoleFormatter.print_warning(w)
            print("ERROR: 処理可能なファイルが見つかりませんでした", file=sys.stderr)
        sys.exit(1)

    verbose_logger.log_file_search(args.list if args.list else f"{len(args.path)} paths", len(tasks))
    
    # 各ファイルの処理
    results = []
    for task in tasks:
        filepath = task["filepath"]
        is_accessible, message = FileScanner.can_access_file(filepath)
        if not is_accessible:
            execution_warnings.append(message)
            continue
        
        try:
            # 個別設定の適用
            file_settings = settings
            if task["overrides"]:
                file_settings = copy.deepcopy(settings)
                if "target_sheets" in task["overrides"]:
                    file_settings["read_definition"]["target_sheets"] = task["overrides"]["target_sheets"]
                if "ignore_sheets" in task["overrides"]:
                    file_settings["read_definition"]["ignore_sheets"] = task["overrides"]["ignore_sheets"]
                if "include_hidden_sheets" in task["overrides"]:
                    file_settings["read_definition"]["include_hidden_sheets"] = task["overrides"]["include_hidden_sheets"]
                if "target_environments" in task["overrides"]:
                    file_settings["read_definition"]["target_environments"] = task["overrides"]["target_environments"]
                if "ignore_environments" in task["overrides"]:
                    file_settings["read_definition"]["ignore_environments"] = task["overrides"]["ignore_environments"]

            result = ReadData.aggregate_results(filepath, file_settings, verbose_logger)
            if task["label"]:
                result["label"] = task["label"]
            if "target_environments" in task["overrides"]:
                result["target_environments"] = task["overrides"]["target_environments"]
            if task.get("subtask_id"):
                result["subtask_id"] = task["subtask_id"]
            results.append((filepath, result))
                
        except Exception as e:
            results.append((filepath, {"error": {"type": "processing_error", "message": f"ファイル処理中にエラーが発生しました: {filepath}", "details": str(e)}}))
            if args.verbose:
                print(f"詳細エラー情報: {traceback.format_exc()}")
    
    if not results:
        if is_json_mode:
            print(json.dumps({"error": "処理可能なファイルが見つかりませんでした", "warnings": execution_warnings}, ensure_ascii=False, indent=2))
        else:
            if execution_warnings:
                print()
                ConsoleFormatter.print_section("Warnings")
                for w in execution_warnings:
                    ConsoleFormatter.print_warning(w)
            print("ERROR: 処理可能なファイルが見つかりませんでした", file=sys.stderr)
        sys.exit(1)

    # 出力データの準備
    is_multiple_files = len(tasks) > 1
    if is_multiple_files:
        output_data = {
            "summary": {
                "processed_files": len(tasks),
                "total_stats": {m: sum(r[1]["stats"][m] for r in results if "stats" in r[1]) for m in ["all", "available", "executed", "completed", "incompleted", "planned"]},
                "overall_status": "",
                "earliest_start_date": min([r[1]["run"]["start_date"] for r in results if "run" in r[1] and r[1]["run"]["start_date"]] or [""]),
                "latest_update": max([r[1]["run"]["last_update"] for r in results if "run" in r[1] and r[1]["run"]["last_update"]] or [""])
            },
            "files": []
        }
        
        # TOTAL RESULTSの統合
        total_res = {k: 0 for k in settings["test_status"]["results"] + ["未実施", "Total", "完了数", "消化数"]}
        for f, r in results:
            if "total" in r:
                for k, v in r["total"].items():
                    if k in total_res and isinstance(v, (int, float)):
                        total_res[k] += v
            file_data = r.copy()
            file_data["file"] = f
            output_data["files"].append(file_data)
        
        if total_res["消化数"] > 0:
            total_res["完了率(%)"] = round(total_res["完了数"] / total_res["消化数"] * 100, 2)
        if output_data["summary"]["total_stats"]["available"] > 0:
            total_res["消化率(%)"] = round(total_res["消化数"] / output_data["summary"]["total_stats"]["available"] * 100, 2)
        output_data["summary"]["total_results"] = total_res
        output_data = output_data # Keep it for clarity
    else:
        f, r = results[0]
        r["file"] = f
        output_data = r

    # ファイル出力処理
    if args.output_file:
        output_writer = OutputWriter(verbose_logger)
        output_file = args.output_file
        output_format = "csv" if args.output_format == "csv" or output_file.endswith('.csv') else "csv"
        if not output_file.endswith('.csv'): output_file += '.csv'
        
        success, error = output_writer.write_csv(output_data, output_file, is_multiple_files, settings)
        if not success:
            print(f"ERROR: {error}", file=sys.stderr)
            sys.exit(1)
        if args.output_format == "csv": sys.exit(0)

    # クリップボード出力
    if args.clipboard:
        clipboard_writer = ClipboardWriter(verbose_logger)
        clipboard_data = []
        for f, r in results:
            r_copy = r.copy()
            r_copy["file"] = f
            clipboard_data.append(r_copy)
        if not clipboard_writer.write_to_clipboard(clipboard_data, settings):
            print("ERROR: クリップボードへのコピーに失敗しました", file=sys.stderr)
            sys.exit(1)

    # 実行時刻の取得
    current_load_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # コンソール出力
    if not is_json_mode:
        if args.output_format == "json":
            print(json.dumps(output_data, ensure_ascii=False, indent=2))
        else:
            if is_multiple_files:
                ConsoleFormatter.print_logo(script_dir)
                ConsoleFormatter.print_report_title("SUMMARY RESULTS")
                if args.list and project_info:
                    ConsoleFormatter.print_key_value("Project", project_info['project_name'])
                    ConsoleFormatter.print_key_value("Processed Files", len(tasks))
                    ConsoleFormatter.print_key_value("Execution Time", current_load_time)
                    print()
                
                ConsoleFormatter.display_combined_total_results(results, settings)
                ConsoleFormatter.display_file_breakdown_table(results, settings)
                ConsoleFormatter.display_error_summary(results)
                
                if args.detailed:
                    for f, r in results:
                        ConsoleFormatter.print_section(os.path.basename(f))
                        ConsoleFormatter.print_summary_results_table(r, f, show_title=False, settings=settings)
            else:
                f, r = results[0]
                ConsoleFormatter.print_summary_results_table(r, f, settings=settings, script_root_dir=script_dir)


    # API連携: WBSサブタスクの進捗更新 (ファイルごと)
    api_config = settings.get("wbs_api", {})
    api_enabled = api_config.get("enabled", True)
    base_url = api_config.get("base_url")
    has_subtasks = any("subtask_id" in r for f, r in results if isinstance(r, dict))
    if api_enabled and base_url and has_subtasks:
        from utils.ApiIntegration import update_subtask_progress
        
        if not is_json_mode:
            print()
            ConsoleFormatter.print_section("API Integration")
        
        api_updates = []
        # 同じファイル・同じサブタスクIDで合算
        api_payloads = {}
        for f, r in results:
            if "subtask_id" in r and "error" not in r and "total" in r:
                subtask_id = r["subtask_id"]
                key = (f, subtask_id)
                
                completed = r["total"].get("完了数", 0)
                available = r.get("stats", {}).get("available", 0)
                start_date = r.get("run", {}).get("start_date")
                
                if key not in api_payloads:
                    api_payloads[key] = {
                        "completed": completed,
                        "available": available,
                        "start_dates": [start_date] if start_date else []
                    }
                else:
                    api_payloads[key]["completed"] += completed
                    api_payloads[key]["available"] += available
                    if start_date:
                        api_payloads[key]["start_dates"].append(start_date)
                        
        for (f, subtask_id), data in api_payloads.items():
            completed = data["completed"]
            available = data["available"]
            progress_percent = (completed / available * 100) if available > 0 else 0
            
            kwargs = {}
            if data["start_dates"]:
                kwargs["actual_start_date"] = min(data["start_dates"])
                
            success, msg = update_subtask_progress(base_url, subtask_id, progress_percent, verbose_logger, **kwargs)
            if is_json_mode:
                api_updates.append({
                    "file": f,
                    "subtask_id": subtask_id,
                    "progress": int(progress_percent),
                    "success": success,
                    "message": msg
                })
            else:
                if not success:
                    ConsoleFormatter.print_warning(f"ファイル '{f}' (サブタスクID: {subtask_id}) の進捗率更新に失敗: {msg}")
                else:
                    ConsoleFormatter.print_info(f"ファイル '{f}' (サブタスクID: {subtask_id}) の進捗率を {int(progress_percent)}% に更新しました。")
        
        if is_json_mode:
            output_data["api_updates"] = api_updates

    if execution_warnings:
        if is_json_mode:
            output_data["warnings"] = execution_warnings
        else:
            print()
            ConsoleFormatter.print_section("Warnings")
            for w in execution_warnings:
                ConsoleFormatter.print_warning(w)

    verbose_logger.end_processing()
    
    if is_json_mode:
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
    else:
        print()

if __name__ == "__main__":
    main()
