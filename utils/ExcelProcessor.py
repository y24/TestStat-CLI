from utils import OpenpyxlWrapper as Excel
from utils import Utility
from . import DataAggregator

def process_sheet(workbook, sheet_name: str, settings: dict, verbose_logger=None):
    """Excelシートのデータ抽出と環境別集計"""
    sheet = Excel.get_sheet_by_name(workbook=workbook, sheet_name=sheet_name)
    header_rownum = Excel.find_row(sheet, search_col=settings["read_definition"]["header"]["search_col"], search_str=settings["read_definition"]["header"]["search_key"])

    if not header_rownum:
        if verbose_logger:
            verbose_logger.log_error_details("header_not_found", "ヘッダー行が見つかりません")
        return {
            "error": {
                "type": "header_not_found",
                "message": f"ヘッダー行が見つかりません。（列:{settings['read_definition']['header']['search_col']} キーワード:{settings['read_definition']['header']['search_key']}）"
            }
        }

    header = Excel.get_row_values(sheet=sheet, row_num=header_rownum)

    if verbose_logger:
        verbose_logger.log_data_range(header_rownum, header_rownum + 1, sheet.max_row, sheet.max_row - header_rownum)

    # 各種列番号の取得
    result_rows = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["result_row"]["keys"], ignore_words=settings["read_definition"]["result_row"]["ignores"])
    person_rows = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["person_row"]["keys"])
    date_rows = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["date_row"]["keys"])
    plan_rows = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["plan_row"]["keys"])

    if verbose_logger:
        verbose_logger.log_column_mapping(header, result_rows, person_rows, date_rows, plan_rows)

    if not Utility.check_lists_equal_length(result_rows, person_rows, date_rows):
        msg = f"結果,担当者,日付のセットが不整合です。（結果:{len(result_rows)} / 担当者:{len(person_rows)} / 日付:{len(date_rows)}）"
        if verbose_logger: verbose_logger.log_error_details("inconsistent_result_set", msg)
        return {"error": {"type": "inconsistent_result_set", "message": msg}}

    if plan_rows and not Utility.check_lists_equal_length(result_rows, plan_rows):
        msg = f"結果列と計画列の数が一致しません。（結果:{len(result_rows)} / 計画:{len(plan_rows)}）"
        if verbose_logger: verbose_logger.log_error_details("inconsistent_plan_set", msg)
        return {"error": {"type": "inconsistent_plan_set", "message": msg}}

    sets = Utility.transpose_lists(result_rows, person_rows, date_rows)
    data, env_data, all_plan_data, sheet_name_mapping = [], {}, [], {}
    
    for index, set_ in enumerate(sets):
        set_data = Excel.get_columns_data(sheet=sheet, col_nums=set_, header_row=header_rownum, ignore_header=True)
        processed_data = [[r[0], r[1] or "NO_NAME", r[2], sheet_name] if r[0] and r[2] and not r[1] else r + [sheet_name] for r in set_data]
        data.extend(processed_data)

        set_name = Excel.get_cell_value(sheet=sheet, col=set_[0], row=1, replace_newline=True) or f"セット{index + 1}"
        plan_data = Excel.get_columns_data(sheet=sheet, col_nums=[plan_rows[index]], header_row=header_rownum, ignore_header=True) if plan_rows else None
        if plan_data: all_plan_data.extend(plan_data)

        env_data[set_name], _ = DataAggregator.get_daily(
            data=processed_data,
            results=settings["test_status"]["results"],
            completed_label=settings["test_status"]["labels"]["completed"], 
            completed_results=settings["test_status"]["completed_results"],
            executed_label=settings["test_status"]["labels"]["executed"],
            executed_results=settings["test_status"]["executed_results"],
            plan_label=settings["test_status"]["labels"]["planned"],
            plan_data=plan_data
        )
        sheet_name_mapping[set_name] = sheet_name

    tobe_rownunms = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["tobe_row"]["keys"])
    if not tobe_rownunms:
        msg = f"期待結果列が見つかりません。（キーワード: {settings['read_definition']['tobe_row']['keys']}）"
        if verbose_logger: verbose_logger.log_error_details("no_tobe_row", msg)
        return {"error": {"type": "no_tobe_row", "message": msg}}

    tobe_data = Excel.get_column_values(sheet=sheet, col_nums=tobe_rownunms, header_row=header_rownum, ignore_header=True)
    case_count = sum(1 for item in tobe_data if any(x is not None for x in item))
    if not case_count:
        msg = f"テストケース数を取得できませんでした。（列番号: {tobe_rownunms}）"
        if verbose_logger: verbose_logger.log_error_details("no_testcases", msg)
        return {"error": {"type": "no_testcases", "message": msg}}

    plan_count = sum(1 for item in all_plan_data if any(x is not None for x in item))

    if verbose_logger:
        valid_dates = len([row for row in data if row[2] and row[2] != "no_date"])
        person_list = list(set([row[1] for row in data if row[1] and row[1] != "NO_NAME"]))
        verbose_logger.log_data_validation(valid_dates, len(data) - valid_dates, person_list, list(env_data.keys()))

    return {
        "data": data, "plan_data": all_plan_data, "env_data": env_data,
        "sheet_name_mapping": sheet_name_mapping,
        "counts": {"sheet_name": sheet_name, "env_count": len(sets), "all": case_count, "all_plan": plan_count}
    }
