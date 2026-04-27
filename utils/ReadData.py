import time
from utils import OpenpyxlWrapper as Excel
from utils import Logger
from utils import Utility
from . import DataAggregator
from . import ExcelProcessor

logger = Logger.get_logger(__name__, console=True, file=False, trace_line=False)

def aggregate_results(filepath:str, settings, verbose_logger=None):
    """Excelファイルからテスト結果データを読み取り、集計する"""
    start_time = time.time()
    if verbose_logger: verbose_logger.start_file_processing(filepath)
    
    workbook = Excel.load(filepath)
    sheet_names = Excel.get_sheetnames_by_keywords(
        workbook, 
        keywords=settings["read_definition"]["sheet_search_keys"], 
        ignores=settings["read_definition"]["sheet_search_ignores"]
    )

    if verbose_logger: verbose_logger.log_excel_info(workbook, sheet_names)

    if not sheet_names:
        msg = f"シートが見つかりませんでした。（キーワード: {settings['read_definition']['sheet_search_keys']}）"
        if verbose_logger: verbose_logger.log_error_details("sheet_not_found", msg)
        return {"error": {"type": "sheet_not_found", "message": msg}}

    all_data, all_plan_data, data_by_env, counts_by_sheet, sheet_name_mapping = [], [], {}, [], {}

    for sheet_name in sheet_names:
        if verbose_logger: verbose_logger.log(f"シート処理開始: {sheet_name}")
        sheet_data = ExcelProcessor.process_sheet(workbook, sheet_name, settings, verbose_logger)
        
        if "error" in sheet_data: return sheet_data
        
        all_data.extend(sheet_data["data"])
        all_plan_data.extend(sheet_data["plan_data"])
        data_by_env.update(sheet_data["env_data"])
        counts_by_sheet.append(sheet_data["counts"])
        sheet_name_mapping.update(sheet_data.get("sheet_name_mapping", {}))
        
        if verbose_logger: verbose_logger.log(f"シート処理完了: {sheet_name} - データ行数: {len(sheet_data['data'])}")

    result = _aggregate_final_results(all_data, all_plan_data, data_by_env, counts_by_sheet, settings, verbose_logger, sheet_name_mapping)
    
    if verbose_logger:
        verbose_logger.end_file_processing()
        verbose_logger.log_performance("データ読み取り・集計", time.time() - start_time)
    
    return result

def _aggregate_final_results(all_data, all_plan_data, data_by_env, counts_by_sheet, settings, verbose_logger=None, sheet_name_mapping=None):
    """全シートの集計データを統合"""
    data_daily_total, no_date_data = DataAggregator.get_daily(
        all_data, settings["test_status"]["results"],
        settings["test_status"]["labels"]["completed"], settings["test_status"]["completed_results"],
        settings["test_status"]["labels"]["executed"], settings["test_status"]["executed_results"],
        settings["test_status"]["labels"]["planned"], all_plan_data
    )

    data_by_name = DataAggregator.get_daily_by_name(all_data)
    data_total = DataAggregator.get_total_all_date(
        data_daily_total, no_date_data,
        [settings["test_status"]["labels"][k] for k in ["completed", "executed", "planned"]]
    )

    case_count_all = sum(item['env_count'] * item['all'] for item in counts_by_sheet)
    excluded_count = DataAggregator.get_excluded_count(all_data, settings["read_definition"]["excluded"])
    available_count = case_count_all - excluded_count
    executed_count = sum(data_total.values())
    completed_count = DataAggregator.sum_completed_results(data_total, settings["test_status"]["completed_results"])
    incompleted_count = max(0, available_count - executed_count)
    total_plan_count = sum(1 for item in all_plan_data if item and item[0] is not None)
    
    count_stats = {
        "all": case_count_all, "excluded": excluded_count, "available": available_count,
        "executed": executed_count, "completed": completed_count, "incompleted": incompleted_count,
        "planned": total_plan_count
    }

    if verbose_logger:
        verbose_logger.log_result_summary(data_total, available_count)
        verbose_logger.log_daily_breakdown(data_daily_total)
        verbose_logger.log_person_summary(data_by_name)
        verbose_logger.log_environment_summary(data_by_env)

    run_status = DataAggregator.make_run_status(count_stats, settings)
    start_date = min(data_daily_total.keys()) if data_daily_total else None
    last_update = max(data_daily_total.keys()) if data_daily_total and run_status in [settings["output_definition"]["state"][k]["name"] for k in ["completed", "in_progress"]] else None

    total_results = {rt: data_total.get(rt, 0) for rt in settings["test_status"]["results"]}
    total_results["未実施"] = incompleted_count
    total_results["Total"] = sum(total_results.values())
    
    completion_rate = (completed_count / available_count * 100) if available_count > 0 else 0
    execution_rate = (executed_count / available_count * 100) if available_count > 0 else 0
    
    total_results.update({
        "完了数": completed_count, "消化数": executed_count,
        "完了率(%)": round(completion_rate, 2), "消化率(%)": round(execution_rate, 2)
    })

    out_data = {
        "stats": count_stats, "run": {"status": run_status, "start_date": start_date, "last_update": last_update},
        "count_by_sheet": counts_by_sheet, "daily": data_daily_total, "total": total_results,
        "by_name": data_by_name, "by_env": data_by_env, "sheet_name_mapping": sheet_name_mapping or {}
    }

    if case_count_all == 0:
        if verbose_logger: verbose_logger.log_warning("項目数を取得できませんでした")
        out_data["warning"] = {"type": "no_data", "message": "項目数を取得できませんでした。"}
    elif executed_count > available_count:
        if verbose_logger: verbose_logger.log_warning("テストケースの完了数が項目数を上回っています")
        out_data["warning"] = {"type": "inconsistent_count", "message": "テストケースの完了数が項目数を上回っています。"}

    return out_data

def aggregate_multiple_files_results(file_results_list: list, settings: dict):
    return DataAggregator.aggregate_multiple_files_results(file_results_list, settings)
