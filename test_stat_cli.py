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

def parse_args():
    # スクリプトのルートディレクトリを取得
    script_dir = get_script_root_dir()
    default_config_path = os.path.join(script_dir, "config.json")
    
    # ヘルプ表示時のみロゴを表示
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        ConsoleFormatter.print_logo(script_dir)
    
    parser = argparse.ArgumentParser(description="Excelテスト仕様書集計ツール")
    parser.add_argument("path", nargs='*', help="集計対象のファイルまたはフォルダのパス（.xlsx または ディレクトリ）。複数指定可能")
    parser.add_argument("-c", "--config", default=default_config_path, help="設定ファイルのパス（デフォルト: ルートフォルダのconfig.json）")
    parser.add_argument("-f", "--output-format", choices=["table", "json", "csv"], default="table", help="出力形式（table/json/csv）")
    parser.add_argument("-o", "--output-file", help="出力ファイルパス")
    parser.add_argument("-j", "--json-output", action="store_true", help="JSON形式で出力")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ出力")
    parser.add_argument("-l", "--list", help="パスリストファイルのパス（YAML形式）")
    parser.add_argument("-p", "--clipboard", action="store_true", help="TSV形式でクリップボードにコピー")
    parser.add_argument("--detailed", action="store_true", help="複数ファイル処理時にファイル別の詳細結果も表示")
    
    return parser.parse_args()

def main():
    args = parse_args()
    script_dir = get_script_root_dir()
    
    # VerboseLoggerの初期化
    verbose_logger = Logger.VerboseLogger(args.verbose)
    verbose_logger.start_processing()
    
    # 設定ファイルの読み込みと検証
    try:
        with open(args.config, encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        print(f"ERROR: 設定ファイルの読み込みに失敗しました: {args.config}\n詳細: {e}")
        sys.exit(1)
    
    is_valid, message = FileScanner.validate_config(settings)
    if not is_valid:
        print(f"ERROR: {message}")
        sys.exit(1)
    
    # ファイルリストの作成
    tasks = []
    project_info = None

    if args.list:
        try:
            project_info = ProjectList.read_project_list_file(args.list)
            for file_info in project_info["files"]:
                target_path = file_info["path"]
                if not os.path.exists(target_path):
                    print(f"WARNING: 指定されたパスが存在しません: {target_path}")
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
                        if "target_environments" in file_info:
                            task["overrides"]["target_environments"] = file_info["target_environments"]
                        if "ignore_environments" in file_info:
                            task["overrides"]["ignore_environments"] = file_info["ignore_environments"]
                            
                        tasks.append(task)
                else:
                    print(f"WARNING: {found_files}")
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    else:
        if not args.path:
            print("ERROR: パスまたはプロジェクトリストファイルを指定してください")
            sys.exit(1)
        for target_path in args.path:
            if not os.path.exists(target_path):
                print(f"WARNING: 指定されたパスが存在しません: {target_path}")
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
                print(f"WARNING: {found_files}")

    if not tasks:
        print("ERROR: 処理可能なファイルが見つかりませんでした")
        sys.exit(1)

    verbose_logger.log_file_search(args.list if args.list else f"{len(args.path)} paths", len(tasks))
    
    # 各ファイルの処理
    results = []
    for task in tasks:
        filepath = task["filepath"]
        is_accessible, message = FileScanner.can_access_file(filepath)
        if not is_accessible:
            print(f"WARNING: {message}")
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
        print("ERROR: 処理可能なファイルが見つかりませんでした")
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
            print(f"ERROR: {error}")
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
            print("ERROR: クリップボードへのコピーに失敗しました")
            sys.exit(1)

    # 実行時刻の取得
    current_load_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # コンソール出力
    if args.output_format == "json" or args.json_output:
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
    else:
        if is_multiple_files:
            ConsoleFormatter.print_logo(script_dir)
            print("=" * 50 + "\nSummary Results\n" + "=" * 50 + "\n")
            if args.list and project_info:
                print(f"Project: {project_info['project_name']}\nProcessed Files: {len(tasks)}")
                print(f"Execution Time: {current_load_time}")
                print()
            
            ConsoleFormatter.display_combined_total_results(results, settings)
            ConsoleFormatter.display_file_breakdown_table(results)
            ConsoleFormatter.display_error_summary(results)
            ConsoleFormatter.display_overall_status(results)
            
            if args.detailed:
                for f, r in results:
                    print("=" * 50)
                    ConsoleFormatter.print_summary_results_table(r, f, show_title=False, settings=settings)
        else:
            f, r = results[0]
            ConsoleFormatter.print_summary_results_table(r, f, settings=settings, script_root_dir=script_dir)


    # API連携: WBSサブタスクの進捗更新 (ファイルごと)
    api_config = settings.get("wbs_api", {})
    base_url = api_config.get("base_url")
    has_subtasks = any("subtask_id" in r for f, r in results if isinstance(r, dict))
    if base_url and has_subtasks:
        from utils.ApiIntegration import update_subtask_progress
        
        print("\n" + "=" * 50)
        print("API Integration")
        print("=" * 50)
        
        for f, r in results:
            if "subtask_id" in r and "error" not in r and "total" in r:
                subtask_id = r["subtask_id"]
                # ユーザーの要望により「完了率」をリクエストする。完了率が存在しない場合は0とする
                progress_percent = r["total"].get("完了率(%)", 0)
                
                kwargs = {}
                start_date = r.get("run", {}).get("start_date")
                if start_date:
                    kwargs["actual_start_date"] = start_date
                
                success, msg = update_subtask_progress(base_url, subtask_id, progress_percent, verbose_logger, **kwargs)
                if not success:
                    print(f"WARNING: ファイル '{f}' (サブタスクID: {subtask_id}) の進捗率更新に失敗: {msg}")
                else:
                    print(f"INFO: ファイル '{f}' (サブタスクID: {subtask_id}) の進捗率を {int(progress_percent)}% に更新しました。")

    verbose_logger.end_processing()
    print()

if __name__ == "__main__":
    main()