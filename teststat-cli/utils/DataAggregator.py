from collections import defaultdict

def aggregate_daily_results(data, results: list[str], completed_label:str, completed_results: list[str], executed_label:str, executed_results: list[str], plan_label:str, plan_data: list[str] = None):
    """日付ごとのデータ集計"""
    result_count = defaultdict(lambda: defaultdict(int))

    def initialize_result_counts(results, date, result_count, completed_label, executed_label, plan_label):
        for key in results:
            result_count[date][key] = result_count[date].get(key, 0)
        result_count[date][completed_label] = result_count[date].get(completed_label, 0)  
        result_count[date][executed_label] = result_count[date].get(executed_label, 0)
        result_count[date][plan_label] = result_count[date].get(plan_label, 0)
        return result_count
    
    for index, row in enumerate(data):
        plan = plan_data[index] if plan_data and index < len(plan_data) else None
        if plan and plan != [None] and len(plan) > 0:
            plan_date = plan[0]
            initialize_result_counts(results, plan_date, result_count, completed_label, executed_label, plan_label)
            result_count[plan_date][plan_label] += 1

        if len(row) >= 4:
            result, name, date = row[0], row[1], row[2]
        else:
            result, name, date = row[0], row[1], row[2]
        
        if not date: date = "no_date"
        initialize_result_counts(results, date, result_count, completed_label, executed_label, plan_label)

        if result in results:
            result_count[date][result] += 1
        if result in completed_results:
            result_count[date][completed_label] += 1
        if result in executed_results:
            result_count[date][executed_label] += 1

    out_data = {}
    no_date_data = {}
    for date, counts in sorted(result_count.items()):
        counts = {**counts}
        if date == "no_date":
            no_date_data = {"no_date": counts}
        else:
            out_data[date] = counts
    return out_data, no_date_data

def aggregate_daily_by_person(data):
    """データ集計（名前別）"""
    date_name_count = defaultdict(lambda: defaultdict(int))
    data = [row for row in data if len(row) > 2 and row[2] not in ("", None)]

    for row in data:
        result, name, date = row[0], row[1], row[2]
        if result:
            date_name_count[date][name] += 1

    out_data = {}
    for date, name_counts in sorted(date_name_count.items()):
        out_data[date] = {name: count for name, count in sorted(name_counts.items())}
    return out_data

def get_excluded_count(data, targets:list[str]) -> int:
    """対象外の数を取得"""
    return sum(1 for row in data if row and row[0] in targets)

def calculate_total_results(data, no_date_data, excludes:list[str]):
    """全日付データ合計"""
    result = {}
    for values in data.values():
        for key, count in values.items():
            result[key] = result.get(key, 0) + count
    if "no_date" in no_date_data:
        for key, count in no_date_data["no_date"].items():
            result[key] = result.get(key, 0) + count
    for exclude in excludes:
        result.pop(exclude, None)
    return result

def sum_completed_results(data: dict, completed_results: list) -> int:
    """完了数を合計"""
    return sum(data.get(key, 0) for key in completed_results)

def determine_run_status(count_stats: dict, settings: dict) -> str:
    """実施状況を判別"""
    if count_stats["executed"] == 0:
        return settings["output_definition"]["state"]["not_started"]["name"]
    elif count_stats["completed"] == count_stats["available"] and count_stats["incompleted"] == 0:
        return settings["output_definition"]["state"]["completed"]["name"]
    elif count_stats["executed"] > 0:
        return settings["output_definition"]["state"]["in_progress"]["name"]
    return "???"

def merge_multiple_file_results(file_results_list: list, settings: dict):
    """複数ファイルの集計結果を統合"""
    combined_total_results = {}
    combined_stats = {k: 0 for k in ["all", "excluded", "available", "executed", "completed", "incompleted", "planned"]}
    completed_count = 0
    executed_count = 0
    
    for file_result in file_results_list:
        for result_type, count in file_result["total"].items():
            if result_type not in ["Total", "完了数", "消化数", "完了率(%)", "消化率(%)"]:
                combined_total_results[result_type] = combined_total_results.get(result_type, 0) + count
        
        for stat_key, count in file_result["stats"].items():
            combined_stats[stat_key] += count
        
        if "daily" in file_result:
            for date_data in file_result["daily"].values():
                for result_type in settings["test_status"]["completed_results"]:
                    completed_count += date_data.get(result_type, 0)
                for result_type in settings["test_status"]["executed_results"]:
                    executed_count += date_data.get(result_type, 0)
    
    combined_total_results["Total"] = sum(v for k, v in combined_total_results.items() if k in settings["test_status"]["results"] or k == "未実施")
    
    available_count = combined_stats["available"]
    completion_rate = (completed_count / available_count * 100) if available_count > 0 else 0
    execution_rate = (executed_count / available_count * 100) if available_count > 0 else 0
    
    combined_total_results.update({
        "完了数": completed_count,
        "消化数": executed_count,
        "完了率(%)": round(completion_rate, 2),
        "消化率(%)": round(execution_rate, 2)
    })
    
    return {"total": combined_total_results, "stats": combined_stats}
