import os
from . import TablePrinter
from . import ConsoleStyle

_LOGO_GRADIENT_START = (95, 210, 202)
_LOGO_GRADIENT_END = (112, 232, 118)
_RESET = "\033[0m"

def print_logo(script_root_dir):
    """ロゴを表示"""
    try:
        logo_path = os.path.join(script_root_dir, "assets", "logo.txt")
        with open(logo_path, "r", encoding="utf-8") as f:
            logo = f.read().rstrip()
            if _use_logo_color():
                logo = _format_logo_gradient(logo)
            print(logo)
            print()
    except FileNotFoundError:
        pass

def _use_logo_color():
    return ConsoleStyle.use_color()

def _format_logo_gradient(logo):
    lines = logo.splitlines()
    width = max((len(line) for line in lines), default=0)
    return "\n".join(_format_logo_line_gradient(line, width) for line in lines)

def _format_logo_line_gradient(line, width):
    if not line:
        return line
    denominator = max(width - 1, 1)
    parts = []
    for index, char in enumerate(line):
        if char == " ":
            parts.append(char)
            continue
        ratio = index / denominator
        red = _interpolate(_LOGO_GRADIENT_START[0], _LOGO_GRADIENT_END[0], ratio)
        green = _interpolate(_LOGO_GRADIENT_START[1], _LOGO_GRADIENT_END[1], ratio)
        blue = _interpolate(_LOGO_GRADIENT_START[2], _LOGO_GRADIENT_END[2], ratio)
        parts.append(f"\033[38;2;{red};{green};{blue}m{char}")
    parts.append(_RESET)
    return "".join(parts)

def _interpolate(start, end, ratio):
    return round(start + (end - start) * ratio)

def print_report_title(title):
    """レポート全体のタイトルを表示"""
    print(ConsoleStyle.color(title, "logo_mint", bold=True))
    print(ConsoleStyle.color("─" * max(TablePrinter.get_display_width(title), 16), "muted"))
    print()

def print_section(title):
    """主要セクション見出しを表示"""
    print(ConsoleStyle.section_title(title))
    print(ConsoleStyle.color("─" * TablePrinter.get_display_width(title), "muted"))

def print_subsection(title):
    """小見出しを表示"""
    print(ConsoleStyle.subsection_title(title))

def print_key_value(label, value):
    print(ConsoleStyle.metric(label, value))

def print_error(message, details=None):
    print(f"{ConsoleStyle.color('ERROR:', 'red', bold=True)} {message}")
    if details:
        print(f"{ConsoleStyle.label('詳細:')} {details}")

def print_warning(message):
    print(f"{ConsoleStyle.color('WARNING:', 'yellow', bold=True)} {message}")

def print_info(message):
    print(f"{ConsoleStyle.color('INFO:', 'cyan', bold=True)} {message}")

def print_summary_results_table(result, filepath, show_title=True, settings=None, script_root_dir=None):
    """集計結果を美しいテーブル形式で出力"""
    if show_title and script_root_dir:
        print_logo(script_root_dir)
        print_report_title("SUMMARY RESULTS")
    
    if "error" in result:
        print_error(result['error']['message'], result["error"].get("details"))
        return
    
    # 基本情報
    print_key_value("File", filepath)
    print_key_value("Total Cases", result['stats']['all'])
    print_key_value("Available Cases", result['stats']['available'])
    print_key_value("Excluded Cases", result['stats']['excluded'])
    print()
    
    # 設定から結果タイプの順序を取得
    result_order = settings["test_status"]["results"] if settings else ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
    
    # 総合結果テーブル
    if 'total' in result:
        print_section("TOTAL RESULTS")
        total_headers = ["Total"] + result_order + ["未実施", "完了数", "消化数"]
        completed = result['total'].get('完了数', 0)
        executed = result['total'].get('消化数', 0)
        completion_rate = result['total'].get('完了率(%)', 0)
        execution_rate = result['total'].get('消化率(%)', 0)
        total_row = [result['total'].get('Total', 0)]
        for rt in result_order:
            total_row.append(result['total'].get(rt, 0))
        total_row.extend([
            result['total'].get('未実施', 0),
            f"{completed} ({completion_rate}%)",
            f"{executed} ({execution_rate}%)"
        ])
        TablePrinter.print_table(total_headers, [total_row])
        print()
    
    # 実施状況
    print(f"{ConsoleStyle.label('STATUS:')} {ConsoleStyle.status(result['run']['status'])}")
    if result['run']['start_date']:
        print_key_value("Start Date", result['run']['start_date'])
    if result['run']['last_update']:
        print_key_value("Last Update", result['run']['last_update'])
    print()
    
    # 日別集計
    if result['daily']:
        print_section("DAILY BREAKDOWN")
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
        print_section("BY NAME")
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
        print_section("BY ENVIRONMENT")
        use_plan_row = settings.get("output_definition", {}).get("use_plan_row", False) if settings else False
        for env_name in sorted(result['by_env'].keys()):
            print()
            print_subsection(env_name)
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
    
    print_section("TOTAL RESULTS")
    total_headers = ["Total"] + result_order + ["未実施", "完了数", "消化数"]
    total_row = [total_results.get("Total", 0)]
    total_row.extend([total_results.get(rt, 0) for rt in result_order])
    total_row.extend([
        total_results.get("未実施", 0),
        f'{total_results.get("完了数", 0)} ({round(completion_rate, 2)}%)',
        f'{total_results.get("消化数", 0)} ({round(execution_rate, 2)}%)'
    ])
    TablePrinter.print_table(total_headers, [total_row])
    print()

def display_file_breakdown_table(results, settings=None):
    """ファイルごとの簡単な内訳を表示"""
    print_section("FILE BREAKDOWN")
    
    result_order = settings["test_status"]["results"] if settings else ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
    headers1 = ["File", "Env", "Total"] + result_order + ["未実施"]
    rows1 = []
    
    headers2 = ["File", "Env", "Total", "Completed", "Executed", "Start Date", "Latest Update"]
    rows2 = []
    
    total_available = 0
    total_completed = 0
    total_executed = 0
    
    all_start_dates = []
    all_latest_updates = []
    
    for filepath, result in results:
        # labelが設定されている場合はそれを使用し、そうでなければファイル名を使用
        base_name = result.get("label") if result.get("label") else os.path.basename(filepath)
        display_name = TablePrinter.shorten_filename(base_name, 30)
        env_val = ", ".join(result.get("target_environments", [])) if result.get("target_environments") else "-"
        
        if "error" in result:
            rows1.append([display_name, env_val, "ERROR"] + ["-"] * (len(result_order) + 1))
            rows2.append([display_name, env_val, "ERROR", "-", "-", "-", "-"])
            continue
        
        available = result.get("stats", {}).get("available", 0)
        total = result.get("total", {})
        
        row1 = [display_name, env_val, available]
        for rt in result_order:
            row1.append(total.get(rt, 0))
        row1.append(total.get("未実施", 0))
        rows1.append(row1)
        
        completed = total.get("完了数", 0)
        executed = total.get("消化数", 0)
        
        total_available += available
        total_completed += completed
        total_executed += executed
        
        comp_rate = round((completed / available * 100), 2) if available > 0 else 0
        exec_rate = round((executed / available * 100), 2) if available > 0 else 0
        
        run_info = result.get("run", {})
        start_date = run_info.get("start_date") or "-"
        last_update = run_info.get("last_update") or "-"
        
        if start_date != "-":
            all_start_dates.append(start_date)
        if last_update != "-":
            all_latest_updates.append(last_update)
        
        rows2.append([display_name, env_val, available, f"{completed} ({comp_rate}%)", f"{executed} ({exec_rate}%)", start_date, last_update])
        
    TablePrinter.print_table(headers1, rows1)
    print()
    print_section("PROGRESS SUMMARY")
    
    total_comp_rate = round((total_completed / total_available * 100), 2) if total_available > 0 else 0
    total_exec_rate = round((total_executed / total_available * 100), 2) if total_available > 0 else 0
    
    min_start_date = min(all_start_dates) if all_start_dates else "-"
    max_last_update = max(all_latest_updates) if all_latest_updates else "-"
    
    rows2.append(["Total", "-", total_available, f"{total_completed} ({total_comp_rate}%)", f"{total_executed} ({total_exec_rate}%)", min_start_date, max_last_update])
    
    TablePrinter.print_table(headers2, rows2, has_total_row=True)
    print()

def display_error_summary(results):
    """エラーが発生したファイルの一覧を表示"""
    error_files = [(os.path.basename(f), r["error"].get("message", ""), r["error"].get("details", "")) for f, r in results if "error" in r]
    if error_files:
        print_section("ERROR SUMMARY")
        print_key_value("Files with errors", len(error_files))
        for filename, message, details in error_files:
            print(f"  - {ConsoleStyle.color(filename, 'red', bold=True)}")
            if message: print(f"    {message}")
            if details: print(f"    {ConsoleStyle.label('(' + details + ')')}")
        print()
