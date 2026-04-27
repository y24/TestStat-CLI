import os
from . import TablePrinter

def print_logo(script_root_dir):
    """ロゴを表示"""
    try:
        logo_path = os.path.join(script_root_dir, "assets", "logo.txt")
        with open(logo_path, "r", encoding="utf-8") as f:
            logo = f.read()
            print(logo)
            print()
    except FileNotFoundError:
        pass

def print_summary_results_table(result, filepath, show_title=True, settings=None, script_root_dir=None):
    """集計結果を美しいテーブル形式で出力"""
    if show_title and script_root_dir:
        print_logo(script_root_dir)
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
        total_headers = ["Total"] + result_order + ["未実施", "完了数", "消化数", "完了率(%)", "消化率(%)"]
        total_row = [result['total'].get('Total', 0)]
        for rt in result_order:
            total_row.append(result['total'].get(rt, 0))
        total_row.extend([
            result['total'].get('未実施', 0),
            result['total'].get('完了数', 0),
            result['total'].get('消化数', 0),
            result['total'].get('完了率(%)', 0),
            result['total'].get('消化率(%)', 0)
        ])
        TablePrinter.print_table(total_headers, [total_row])
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
        daily_headers = ["Date"] + result_order + ["完了数", "消化数"]
        use_plan_row = settings.get("output_definition", {}).get("use_plan_row", False) if settings else False
        if use_plan_row:
            daily_headers.append("計画数")
        
        daily_rows = []
        for date in sorted(result['daily'].keys()):
            row = [date]
            for rt in result_order:
                row.append(result['daily'][date].get(rt, 0))
            row.extend([result['daily'][date].get('完了数', 0), result['daily'][date].get('消化数', 0)])
            if use_plan_row:
                row.append(result['daily'][date].get('計画数', 0))
            daily_rows.append(row)
        TablePrinter.print_table(daily_headers, daily_rows)
        print()
    
    # 担当者別集計
    if result['by_name']:
        print("BY NAME:")
        all_names = sorted({name for date_data in result['by_name'].values() for name in date_data.keys()})
        name_headers = ["Date"] + all_names
        name_rows = []
        for date in sorted(result['by_name'].keys()):
            row = [date] + [result['by_name'][date].get(name, 0) for name in all_names]
            name_rows.append(row)
        TablePrinter.print_table(name_headers, name_rows)
        print()
    
    # 環境別集計
    if result['by_env']:
        print("BY ENVIRONMENT:")
        use_plan_row = settings.get("output_definition", {}).get("use_plan_row", False) if settings else False
        for env_name in sorted(result['by_env'].keys()):
            print(f"\n{env_name}:")
            env_headers = ["Date"] + result_order + ["完了数", "消化数"]
            if use_plan_row:
                env_headers.append("計画数")
            env_rows = []
            for date in sorted(result['by_env'][env_name].keys()):
                row = [date]
                for rt in result_order:
                    row.append(result['by_env'][env_name][date].get(rt, 0))
                row.extend([result['by_env'][env_name][date].get('完了数', 0), result['by_env'][env_name][date].get('消化数', 0)])
                if use_plan_row:
                    row.append(result['by_env'][env_name][date].get('計画数', 0))
                env_rows.append(row)
            TablePrinter.print_table(env_headers, env_rows)
        print()

def display_combined_total_results(results, settings=None):
    """複数ファイルの総合結果を表示"""
    result_order = settings["test_status"]["results"] if settings else ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
    total_results = {rt: 0 for rt in result_order}
    for key in ["未実施", "Total", "完了数", "消化数"]:
        total_results[key] = 0
    
    total_available = 0
    for filepath, result in results:
        if "total" in result:
            for rt in result_order:
                total_results[rt] += result["total"].get(rt, 0)
            for key in ["未実施", "Total", "完了数", "消化数"]:
                total_results[key] += result["total"].get(key, 0)
        if "stats" in result:
            total_available += result["stats"].get("available", 0)
    
    completion_rate = (total_results["完了数"] / total_available * 100) if total_available > 0 else 0
    execution_rate = (total_results["消化数"] / total_available * 100) if total_available > 0 else 0
    
    print("SUMMARY TOTAL RESULTS:")
    total_headers = ["Total"] + result_order + ["未実施", "完了数", "消化数", "完了率(%)", "消化率(%)"]
    total_row = [total_results.get("Total", 0)]
    total_row.extend([total_results.get(rt, 0) for rt in result_order])
    total_row.extend([
        total_results.get("未実施", 0),
        total_results.get("完了数", 0),
        total_results.get("消化数", 0),
        round(completion_rate, 2),
        round(execution_rate, 2)
    ])
    TablePrinter.print_table(total_headers, [total_row])
    print()

def display_file_breakdown_table(results):
    """ファイルごとの簡単な内訳を表示"""
    print("FILE BREAKDOWN:")
    headers = ["File", "Available Cases", "Completed", "Completion Rate(%)", "Executed", "Execution Rate(%)"]
    rows = []
    for filepath, result in results:
        # labelが設定されている場合はそれを使用し、そうでなければファイル名を使用
        base_name = result.get("label") if result.get("label") else os.path.basename(filepath)
        display_name = TablePrinter.shorten_filename(base_name, 30)
        if "error" in result:
            rows.append([display_name, "ERROR", "-", "-", "-", "-"])
            continue
        
        available = result.get("stats", {}).get("available", 0)
        completed = result.get("total", {}).get("完了数", 0)
        executed = result.get("total", {}).get("消化数", 0)
        
        comp_rate = round((completed / available * 100), 2) if available > 0 else 0
        exec_rate = round((executed / available * 100), 2) if available > 0 else 0
        
        rows.append([display_name, available, completed, comp_rate, executed, exec_rate])
    TablePrinter.print_table(headers, rows)
    print()

def display_error_summary(results):
    """エラーが発生したファイルの一覧を表示"""
    error_files = [(os.path.basename(f), r["error"].get("message", ""), r["error"].get("details", "")) for f, r in results if "error" in r]
    if error_files:
        print("ERROR SUMMARY:")
        print(f"Files with errors: {len(error_files)}")
        for filename, message, details in error_files:
            print(f"  - {filename}")
            if message: print(f"    {message}")
            if details: print(f"    ({details})")
        print()

def display_overall_status(results):
    """全体ステータスを表示"""
    statuses = [r["run"]["status"] for f, r in results if "run" in r and r["run"]["status"]]
    if statuses:
        overall_status = "Completed" if all(s == "完了" for s in statuses) else ("In Progress" if any(s == "進行中" for s in statuses) else statuses[0])
    else:
        overall_status = "Unknown"
    
    start_dates = [r["run"]["start_date"] for f, r in results if "run" in r and r["run"]["start_date"]]
    last_updates = [r["run"]["last_update"] for f, r in results if "run" in r and r["run"]["last_update"]]
    
    print(f"OVERALL STATUS: {overall_status}")
    if start_dates: print(f"Earliest Start Date: {min(start_dates)}")
    if last_updates: print(f"Latest Update: {max(last_updates)}")
    print()
