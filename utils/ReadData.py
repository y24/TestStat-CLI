from collections import defaultdict
import pprint
import time
from datetime import datetime

from utils import OpenpyxlWrapper as Excel
from utils import Logger
from utils import Utility

logger = Logger.get_logger(__name__, console=True, file=False, trace_line=False)

# 日付ごとのデータ集計
def get_daily(data, results: list[str], completed_label:str, completed_results: list[str], executed_label:str, executed_results: list[str], plan_label:str, plan_data: list[str] = None):
    # 辞書を初期化：{日付: {結果タイプ: カウント}}
    result_count = defaultdict(lambda: defaultdict(int))

    def initialize_result_counts(results, date, result_count, completed_label, executed_label, plan_label):
        # 各結果タイプのカウントを0で初期化
        for key in results:
            result_count[date][key] = result_count[date].get(key, 0)
        result_count[date][completed_label] = result_count[date].get(completed_label, 0)  
        result_count[date][executed_label] = result_count[date].get(executed_label, 0)
        result_count[date][plan_label] = result_count[date].get(plan_label, 0)
        return result_count
    
    for index, row in enumerate(data):
        # 計画データの日付別集計
        plan = plan_data[index] if plan_data and index < len(plan_data) else None
        if plan and plan != [None] and len(plan) > 0:
            plan_date = plan[0]
            # 各実績値は0で初期化
            result_count = initialize_result_counts(results, plan_date, result_count, completed_label, executed_label, plan_label)
            # 計画数をカウント
            result_count[plan_date][plan_label] += 1

        # 実績データの日付別集計
        if len(row) >= 4:
            result, name, date, sheet_name = row[0], row[1], row[2], row[3]
        else:
            # 後方互換性のため、シート名がない場合は空文字を設定
            result, name, date = row[0], row[1], row[2]
            sheet_name = ""
        
        # 日付が未設定の場合は特別な識別子「no_date」として扱う
        if not date: date = "no_date"
        # 各結果タイプのカウントを0で初期化
        result_count = initialize_result_counts(results, date, result_count, completed_label, executed_label, plan_label)

        # 結果の集計処理
        # 1. 個別の結果タイプをカウント
        if result in results:
            result_count[date][result] += 1
        # 2. 完了としてカウントすべき結果の場合、"完了数"としてもカウント
        if result in completed_results:
            result_count[date][completed_label] += 1
        # 3. 消化としてカウントすべき結果の場合、"消化数"としてもカウント
        if result in executed_results:
            result_count[date][executed_label] += 1

    # 集計結果を日付ありデータと日付なしデータに分離
    out_data = {}      # 日付ありデータ
    no_date_data = {}  # 日付なしデータ
    for date, counts in sorted(result_count.items()):
        counts = {**counts}  # 辞書のディープコピー
        if date == "no_date":
            no_date_data = {"no_date": counts}  # 日付なしデータは"no_date"キーに格納
        else:
            out_data[date] = counts
    return out_data, no_date_data

# データ集計（名前別）
def get_daily_by_name(data):
    date_name_count = defaultdict(lambda: defaultdict(int))

    # 日付が空の行は削除
    data = [row for row in data if len(row) > 2 and row[2] not in ("", None)]

    # 結果が空ではない行を日付および名前ごとにカウント
    for row in data:
        if len(row) >= 4:
            result, name, date, sheet_name = row[0], row[1], row[2], row[3]
        else:
            # 後方互換性のため、シート名がない場合は空文字を設定
            result, name, date = row[0], row[1], row[2]
            sheet_name = ""
        if result:  # 結果が空ではない場合
            date_name_count[date][name] += 1

    # 集計結果を返却
    out_data = {}
    for date, name_counts in sorted(date_name_count.items()):
        daily_count = {}
        for name, count in sorted(name_counts.items()):
            daily_count[name] = count
        out_data[date] = daily_count
    return out_data

# 対象外の数を取得
def get_excluded_count(data, targets:list[str]) -> int:
    return sum(1 for row in data if row and row[0] in targets)

# 全日付データ合計
def get_total_all_date(data, no_date_data, excludes:list[str]):
    result = {}
    # 全日付データ
    for values in data.values():
        for key, count in values.items():
            result[key] = result.get(key, 0) + count
    # 日付なしデータ
    if "no_date" in no_date_data:
        for key, count in no_date_data["no_date"].items():
            result[key] = result.get(key, 0) + count
    # Completedは除く
    for exclude in excludes:
        result.pop(exclude, None)
    return result

# 完了数を合計
def sum_completed_results(data: dict, completed_results: list) -> int:
    return sum(data.get(key, 0) for key in completed_results)

# 実施状況を判別
def make_run_status(count_stats: dict, settings: dict) -> str:
    if count_stats["executed"] == 0:
        # 未着手
        return settings["output_definition"]["state"]["not_started"]["name"]
    elif count_stats["completed"] == count_stats["available"] and count_stats["incompleted"] == 0:
        # 完了
        return settings["output_definition"]["state"]["completed"]["name"]
    elif count_stats["executed"] > 0:
        # 進行中
        return settings["output_definition"]["state"]["in_progress"]["name"]
    else:
        return "???"

# Excelファイルからテスト結果データを読み取り、集計する関数
def aggregate_results(filepath:str, settings, verbose_logger=None, filters=None):
    start_time = time.time()
    
    # 詳細ログ開始
    if verbose_logger:
        verbose_logger.start_file_processing(filepath)
    
    # フィルタリング条件の詳細ログ
    if verbose_logger and filters:
        verbose_logger.log("フィルタ条件適用開始")
        if "date_range" in filters:
            start = filters["date_range"]["start"]
            end = filters["date_range"]["end"]
            if start and end:
                verbose_logger.log(f"- 日付範囲: {start} から {end}")
            elif start:
                verbose_logger.log(f"- 日付範囲: {start} onwards (開始日のみ)")
            elif end:
                verbose_logger.log(f"- 日付範囲: up to {end} (終了日のみ)")
        
        if "tester" in filters:
            match_type = "完全一致" if filters["tester"]["exact_match"] else "部分一致"
            verbose_logger.log(f"- 担当者: {filters['tester']['value']} ({match_type})")
        
        if "result_type" in filters:
            if len(filters["result_type"]) == 1:
                verbose_logger.log(f"- 結果タイプ: {filters['result_type'][0]} (単一)")
            else:
                verbose_logger.log(f"- 結果タイプ: {', '.join(filters['result_type'])} (複数)")
        
        if "environment" in filters:
            match_type = "完全一致" if filters["environment"]["exact_match"] else "部分一致"
            verbose_logger.log(f"- 環境: {filters['environment']['value']} ({match_type})")
    
    # 設定された検索キーワードに基づいて対象シートを特定
    workbook = Excel.load(filepath)
    sheet_names = Excel.get_sheetnames_by_keywords(
        workbook, 
        keywords=settings["read_definition"]["sheet_search_keys"], 
        ignores=settings["read_definition"]["sheet_search_ignores"]
    )

    # Excelファイル情報をログ出力
    if verbose_logger:
        verbose_logger.log_excel_info(workbook, sheet_names)

    # 対象シートが見つからない場合はエラーを返却
    if len(sheet_names) == 0:
        if verbose_logger:
            verbose_logger.log_error_details("sheet_not_found", f"シートが見つかりませんでした。（キーワード: {settings['read_definition']['sheet_search_keys']}）")
        return {
            "error": {
                "type": "sheet_not_found",
                "message": f"シートが見つかりませんでした。（キーワード: {settings['read_definition']['sheet_search_keys']}）"
            }
        }

    # 集計用の変数を初期化
    all_data = []          # 全シートの生データを格納
    all_plan_data = []     # 全シートの計画データを格納
    data_by_env = {}       # 環境別の集計データを格納
    counts_by_sheet = []   # シート別の件数情報を格納
    sheet_name_mapping = {} # 環境名とシート名のマッピング

    # 各シートのデータを処理
    for sheet_name in sheet_names:
        if verbose_logger:
            verbose_logger.log(f"シート処理開始: {sheet_name}")
        
        # シートごとのデータを処理して取得
        sheet_data = _process_sheet(workbook=workbook, sheet_name=sheet_name, settings=settings, verbose_logger=verbose_logger)
        
        # エラーが発生した場合は即時返却
        if "error" in sheet_data:
            if verbose_logger:
                verbose_logger.log_error_details(sheet_data["error"]["type"], sheet_data["error"]["message"])
            return sheet_data
        # 正常にデータが取得できた場合は集計用変数に追加
        elif sheet_data:
            all_data.extend(sheet_data["data"])           # 結果データを追加
            all_plan_data.extend(sheet_data["plan_data"]) # 計画データを追加
            data_by_env.update(sheet_data["env_data"])    # 環境別データを追加
            counts_by_sheet.append(sheet_data["counts"])   # 件数情報を追加
            sheet_name_mapping.update(sheet_data.get("sheet_name_mapping", {}))  # シート名マッピングを追加
            
            if verbose_logger:
                verbose_logger.log(f"シート処理完了: {sheet_name} - データ行数: {len(sheet_data['data'])}")

    # フィルタリング処理
    if filters:
        all_data, all_plan_data, data_by_env = apply_filters(all_data, all_plan_data, data_by_env, filters, verbose_logger)

    # 全シートの集計データを生成して返却
    result = _aggregate_final_results(
            all_data=all_data,           # 全シートの結果データ
            all_plan_data=all_plan_data, # 全シートの計画データ
            data_by_env=data_by_env,     # 環境別の集計データ(計画を含む)
            counts_by_sheet=counts_by_sheet,  # シート別のテストケース件数情報
            settings=settings,            # 設定情報
            verbose_logger=verbose_logger, # 詳細ログ
            filters=filters,             # フィルタリング条件
            sheet_name_mapping=sheet_name_mapping  # シート名マッピング
        )
    
    # 詳細ログ終了
    if verbose_logger:
        verbose_logger.end_file_processing()
        elapsed = time.time() - start_time
        verbose_logger.log_performance("データ読み取り・集計", elapsed)
    
    return result

def _process_sheet(workbook, sheet_name: str, settings: dict, verbose_logger=None):
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

    # ヘッダ行を取得
    header = Excel.get_row_values(sheet=sheet, row_num=header_rownum)

    # データ範囲情報をログ出力
    if verbose_logger:
        # シートの最大行数を取得
        max_row = sheet.max_row
        data_start = header_rownum + 1
        data_end = max_row
        total_rows = data_end - data_start + 1
        verbose_logger.log_data_range(header_rownum, data_start, data_end, total_rows)

    # 列番号(例:環境別)を取得
    # 結果
    result_rows = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["result_row"]["keys"], ignore_words=settings["read_definition"]["result_row"]["ignores"])
    # 担当者
    person_rows = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["person_row"]["keys"])
    # 日付
    date_rows = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["date_row"]["keys"])
    # 計画
    plan_rows = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["plan_row"]["keys"])

    # 列マッピング情報をログ出力
    if verbose_logger:
        verbose_logger.log_column_mapping(header, result_rows, person_rows, date_rows, plan_rows)

    # 結果,担当者,日付の列セットが見つからないor同数でない場合はエラー
    if Utility.check_lists_equal_length(result_rows, person_rows, date_rows) == False:
        if verbose_logger:
            verbose_logger.log_error_details("inconsistent_result_set", 
                f"結果,担当者,日付のセットが正しく取得できません。（結果: {len(result_rows)}列 / 担当者: {len(person_rows)}列 / 日付: {len(date_rows)}列）")
        return {
            "error": {
                "type": "inconsistent_result_set",
                "message": f"結果,担当者,日付のセットが正しく取得できません。（結果: {len(result_rows)}列 / 担当者: {len(person_rows)}列 / 日付: {len(date_rows)}列）"
            }
        }

    # 計画列がある場合、結果列と計画列のセット数が一致しない場合はエラー
    if plan_rows and Utility.check_lists_equal_length(result_rows, plan_rows) == False:
        if verbose_logger:
            verbose_logger.log_error_details("inconsistent_plan_set", 
                f"結果列に対して計画列の数が一致しません。（結果: {len(result_rows)}列 / 計画: {len(plan_rows)}列）")
        return {
            "error": {
                "type": "inconsistent_plan_set",
                "message": f"結果列に対して計画列の数が一致しません。（結果: {len(result_rows)}列 / 計画: {len(plan_rows)}列）"
            }
        }

    # 列番号のセット(結果、担当者、日付)を作成
    sets = Utility.transpose_lists(result_rows, person_rows, date_rows)

    # 各セット処理
    data = []
    env_data = {}  # 環境データを格納する辞書を初期化
    all_plan_data = []
    sheet_name_mapping = {}  # 環境名とシート名のマッピング
    
    for index, set_ in enumerate(sets):
        # セットのデータ取得
        set_data = Excel.get_columns_data(sheet=sheet, col_nums=set_, header_row=header_rownum, ignore_header=True)

        # 担当者名がNoneで結果と日付が存在する場合、"NO_NAME"に置き換え
        # 各データ行にシート名を追加
        processed_data = []
        for row in set_data:
            if row[0] is not None and row[2] is not None and row[1] is None:
                row = [row[0], "NO_NAME", row[2]]
            # シート名を4番目の要素として追加
            row_with_sheet = row + [sheet_name]
            processed_data.append(row_with_sheet)

        # 全セット合計のデータにも追加
        data.extend(processed_data)

        # そのセットの1行目からセット名を取得(セル内改行は_に置換)
        set_name = Excel.get_cell_value(sheet=sheet, col=set_[0], row=1, replace_newline=True)

        # セット名がない場合はシート名をセット
        if not set_name:
            set_name = f"セット{index + 1}"

        # 計画列がある場合
        if len(plan_rows) > 0:
            # 計画データを取得
            plan_data = Excel.get_columns_data(sheet=sheet, col_nums=[plan_rows[index]], header_row=header_rownum, ignore_header=True)
            all_plan_data.extend(plan_data)
        else:
            plan_data = None

        # 環境ごとのデータ集計
        env_data[set_name], _ = get_daily(
            data=processed_data,
            results=settings["test_status"]["results"],
            completed_label=settings["test_status"]["labels"]["completed"], 
            completed_results=settings["test_status"]["completed_results"],
            executed_label=settings["test_status"]["labels"]["executed"],
            executed_results=settings["test_status"]["executed_results"],
            plan_label=settings["test_status"]["labels"]["planned"],
            plan_data=plan_data
        )
        
        # 環境名とシート名のマッピングを保存
        sheet_name_mapping[set_name] = sheet_name

    # 環境数
    env_count = len(sets)

    # 期待結果列の番号
    tobe_rownunms = Utility.find_colnum_by_keywords(lst=header, keywords=settings["read_definition"]["tobe_row"]["keys"])

    if not tobe_rownunms:
        if verbose_logger:
            verbose_logger.log_error_details("no_tobe_row", 
                f"期待結果列が見つかりませんでした。（キーワード: {settings['read_definition']['tobe_row']['keys']}）")
        return {
            "error": {
                "type": "no_tobe_row",
                "message": f"期待結果列が見つかりませんでした。（キーワード: {settings['read_definition']['tobe_row']['keys']}）"
            }
        }

    # 期待結果データ
    tobe_data = Excel.get_column_values(sheet=sheet, col_nums=tobe_rownunms,header_row=header_rownum, ignore_header=True)
    # テストケース数を計算
    case_count = sum(1 for item in tobe_data if any(x is not None for x in item))

    if not case_count:
        if verbose_logger:
            verbose_logger.log_error_details("no_testcases", 
                f"テストケース数を取得できませんでした。（列番号: {tobe_rownunms}）")
        return {
            "error": {
                "type": "no_testcases",
                "message": f"テストケース数を取得できませんでした。（列番号: {tobe_rownunms}）"
            }
        }

    # 計画データ
    # 計画数をカウント
    plan_count = sum(1 for item in all_plan_data if any(x is not None for x in item))

    # データ検証情報をログ出力
    if verbose_logger:
        # 日付データの検証
        valid_dates = len([row for row in data if row[2] and row[2] != "no_date"])
        invalid_dates = len([row for row in data if not row[2] or row[2] == "no_date"])
        
        # 担当者データの抽出
        person_list = list(set([row[1] for row in data if row[1] and row[1] != "NO_NAME"]))
        
        # 環境データの抽出
        environment_list = list(env_data.keys())
        
        verbose_logger.log_data_validation(valid_dates, invalid_dates, person_list, environment_list)

    # 結果を返却
    return {
        "data": data,
        "plan_data": all_plan_data,
        "env_data": env_data,
        "sheet_name_mapping": sheet_name_mapping,
        "counts": {
            "sheet_name": sheet_name,
            "env_count": env_count,
            "all": case_count,
            "all_plan": plan_count
        }
    }

def _aggregate_final_results(all_data, all_plan_data, data_by_env, counts_by_sheet, settings, verbose_logger=None, filters=None, sheet_name_mapping=None):
    # 全セット集計(日付別)
    data_daily_total, no_date_data = get_daily(
        data=all_data,
        results=settings["test_status"]["results"],
        completed_label=settings["test_status"]["labels"]["completed"],
        completed_results=settings["test_status"]["completed_results"],
        executed_label=settings["test_status"]["labels"]["executed"],
        executed_results=settings["test_status"]["executed_results"],
        plan_label=settings["test_status"]["labels"]["planned"],
        plan_data=all_plan_data
    )

    # 全セット集計(担当者別)
    data_by_name = get_daily_by_name(all_data)
    
    # 全セット集計(全日付＋日付なし)
    data_total = get_total_all_date(
        data=data_daily_total,
        no_date_data=no_date_data,
        excludes=[
            settings["test_status"]["labels"]["completed"],
            settings["test_status"]["labels"]["executed"],
            settings["test_status"]["labels"]["planned"]
        ]
    )

    # 総テストケース数
    case_count_all = sum(item['env_count'] * item['all'] for item in counts_by_sheet)
    # 対象外テストケース数
    excluded_count = get_excluded_count(data=all_data, targets=settings["read_definition"]["excluded"])
    # 有効テストケース数
    available_count = case_count_all - excluded_count
    # 消化テストケース数
    executed_count = sum(data_total.values())
    # 完了テストケース数
    completed_count = sum_completed_results(data_total, settings["test_status"]["completed_results"])
    # 未実施テストケース数(マイナスは0)
    incompleted_count = max(0, available_count - executed_count)
    # 総計画数
    total_plan_count = sum(1 for item in all_plan_data if item and item[0] is not None)
    # 集計データ
    count_stats = {
        "all": case_count_all,
        "excluded": excluded_count,
        "available": available_count,
        "executed": executed_count,
        "completed": completed_count,
        "incompleted": incompleted_count,
        "planned": total_plan_count
    }

    # 詳細ログ出力
    if verbose_logger:
        verbose_logger.log_result_summary(data_total, available_count)
        verbose_logger.log_daily_breakdown(data_daily_total)
        verbose_logger.log_person_summary(data_by_name)
        verbose_logger.log_environment_summary(data_by_env)

    # 実施状況
    run_status = make_run_status(count_stats, settings)

    # 開始日・最終更新日
    start_date = None
    last_update = None
    # 日付別データがある場合
    if not Utility.is_empty(data_daily_total):
        # 開始日を取得
        start_date = min(data_daily_total.keys())
        # かつステータスが完了または進行中の場合
        if run_status == settings["output_definition"]["state"]["completed"]["name"] or run_status == settings["output_definition"]["state"]["in_progress"]["name"]:
            # 最終更新日を取得
            last_update = max(data_daily_total.keys())

    # 実施状況データ
    run_data = {
        "status": run_status,
        "start_date": start_date,
        "last_update": last_update
    }

    # 環境別データをそのまま使用（変換しない）
    by_env_daily = data_by_env

    # 総合結果データ（Pass、Fixed、Fail、Blocked、Suspend、N/Aの合計）
    total_results = {}
    for result_type in settings["test_status"]["results"]:
        total_results[result_type] = data_total.get(result_type, 0)
    total_results["Total"] = sum(total_results.values())
    
    # 完了率と消化率を計算
    completion_rate = (completed_count / available_count * 100) if available_count > 0 else 0
    execution_rate = (executed_count / available_count * 100) if available_count > 0 else 0
    
    # 完了数と消化数を追加
    total_results["完了数"] = completed_count
    total_results["消化数"] = executed_count
    total_results["完了率(%)"] = round(completion_rate, 2)
    total_results["消化率(%)"] = round(execution_rate, 2)

    # 最終出力データ
    out_data = {
        "stats": count_stats,
        "run": run_data,
        "count_by_sheet": counts_by_sheet,
        "daily": data_daily_total,
        "total": total_results,
        "by_name": data_by_name,
        "by_env": by_env_daily,
        "sheet_name_mapping": sheet_name_mapping or {}
    }

    # フィルタ適用後の統計情報を追加
    if filters:
        filtered_count = len(all_data)
        out_data["filtered_stats"] = {
            "filtered_count": filtered_count,
            "original_count": case_count_all
        }

    # データチェック
    if case_count_all == 0:
        if verbose_logger:
            verbose_logger.log_warning("項目数を取得できませんでした")
        out_data["warning"] = {"type": "no_data", "message": "項目数を取得できませんでした。"}
    elif executed_count > available_count:
        if verbose_logger:
            verbose_logger.log_warning("テストケースの完了数が項目数を上回っています")
        out_data["warning"] = {"type": "inconsistent_count", "message": "テストケースの完了数が項目数を上回っています。"}

    return out_data

# コンソール出力
def console_out(data):
    filename = data["file"]
    logger.info(f"FILE: {filename}")
    logger.info(f"CASES COUNT: {data['count']}")
    logger.debug(" ")

    # インデント
    dep = "  "

    # 全セット
    if any(data["total"]):
        logger.info("[Total]")
        for key, d in data["total"].items():
            logger.debug(dep + f"{key}: {d}")
        logger.debug(" ")

        logger.info("[By name]")
        for key, d in data["by_name"].items():
            logger.debug(dep + f"{key}: {d}")
        logger.debug(" ")

    # 出力(セット別)
    if any(data["by_env"]):
        logger.info("[By environment]")
        for key, d in data["by_env"].items():
            logger.debug(dep + f"{key}:")
            for key, d in d.items():
                logger.debug(dep * 2 + f"{key}: {d}")
        logger.debug(" ")

    logger.debug(" ")
    logger.info("~" * 50)

# 複数ファイルの集計値を計算する関数
def aggregate_multiple_files_results(file_results_list: list, settings: dict):
    """
    複数ファイルの集計結果を統合して、全体の集計値を計算する
    
    Args:
        file_results_list: 各ファイルの集計結果のリスト
        settings: 設定情報
    
    Returns:
        dict: 統合された集計結果
    """
    # 統合用の変数を初期化
    combined_total_results = {}
    combined_stats = {
        "all": 0,
        "excluded": 0,
        "available": 0,
        "executed": 0,
        "completed": 0,
        "incompleted": 0,
        "planned": 0
    }
    
    # 完了数と消化数の集計用変数
    completed_count = 0
    executed_count = 0
    
    # 各ファイルの結果を統合
    for file_result in file_results_list:
        # total_resultsの統合
        for result_type, count in file_result["total"].items():
            if result_type != "Total":  # Totalは後で計算
                combined_total_results[result_type] = combined_total_results.get(result_type, 0) + count
        
        # statsの統合
        for stat_key, count in file_result["stats"].items():
            combined_stats[stat_key] += count
        
        # 完了数と消化数を各ファイルのdailyデータから集計
        if "daily" in file_result:
            for date_data in file_result["daily"].values():
                # 完了数（completed_resultsに含まれる結果の合計）
                for result_type in settings["test_status"]["completed_results"]:
                    completed_count += date_data.get(result_type, 0)
                
                # 消化数（executed_resultsに含まれる結果の合計）
                for result_type in settings["test_status"]["executed_results"]:
                    executed_count += date_data.get(result_type, 0)
    
    # Totalを計算
    combined_total_results["Total"] = sum(combined_total_results.values())
    
    # 完了率と消化率を計算
    available_count = combined_stats["available"]
    completion_rate = (completed_count / available_count * 100) if available_count > 0 else 0
    execution_rate = (executed_count / available_count * 100) if available_count > 0 else 0
    
    # 完了数と消化数をtotal_resultsに追加
    combined_total_results["完了数"] = completed_count
    combined_total_results["消化数"] = executed_count
    combined_total_results["完了率(%)"] = round(completion_rate, 2)
    combined_total_results["消化率(%)"] = round(execution_rate, 2)
    
    return {
        "total": combined_total_results,
        "stats": combined_stats
    }

def apply_filters(all_data, all_plan_data, data_by_env, filters, verbose_logger=None):
    """フィルタリング条件を適用してデータを絞り込み"""
    if not filters:
        return all_data, all_plan_data, data_by_env
    
    original_count = len(all_data)
    filtered_data = []
    filtered_plan_data = []
    filtered_env_data = {}
    
    # 詳細ログ
    if verbose_logger:
        verbose_logger.log(f"フィルタ適用前データ: {original_count}件")
    
    for i, row in enumerate(all_data):
        # データ行の構造: (result, name, date, sheet_name)
        if len(row) >= 4:
            result, name, date, sheet_name = row[0], row[1], row[2], row[3]
        else:
            # 後方互換性のため、シート名がない場合は空文字を設定
            result, name, date = row[0], row[1], row[2]
            sheet_name = ""
        
        # 各フィルタ条件をチェック
        include_row = True
        
        # 日付範囲フィルタ
        if "date_range" in filters and include_row:
            include_row = check_date_filter(date, filters["date_range"], verbose_logger)
        
        # 担当者フィルタ
        if "tester" in filters and include_row:
            include_row = check_tester_filter(name, filters["tester"], verbose_logger)
        
        # 結果タイプフィルタ
        if "result_type" in filters and include_row:
            include_row = check_result_type_filter(result, filters["result_type"], verbose_logger)
        
        # 環境フィルタ
        if "environment" in filters and include_row:
            include_row = check_environment_filter(name, filters["environment"], verbose_logger)
        
        # フィルタ条件を満たす場合は結果に含める
        if include_row:
            filtered_data.append((result, name, date, sheet_name))
            if i < len(all_plan_data):
                filtered_plan_data.append(all_plan_data[i])
    
    # 環境別データの再構築
    for env_name, env_data in data_by_env.items():
        filtered_env_data[env_name] = {}
        for date, date_data in env_data.items():
            filtered_env_data[env_name][date] = {}
            for result_type, count in date_data.items():
                # 結果タイプフィルタが指定されている場合は該当する結果タイプのみを含める
                if "result_type" in filters:
                    if result_type in filters["result_type"]:
                        filtered_env_data[env_name][date][result_type] = count
                else:
                    filtered_env_data[env_name][date][result_type] = count
    
    # 詳細ログ
    if verbose_logger:
        filtered_count = len(filtered_data)
        reduction_percent = ((original_count - filtered_count) / original_count * 100) if original_count > 0 else 0
        verbose_logger.log(f"フィルタ適用後データ: {filtered_count}件 ({reduction_percent:.1f}%削減)")
    
    return filtered_data, filtered_plan_data, filtered_env_data

def check_date_filter(date, date_range, verbose_logger=None):
    """日付範囲フィルタをチェック"""
    if not date:
        return False
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        start_date = date_range["start"]
        end_date = date_range["end"]
        
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            if target_date < start:
                return False
        
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if target_date > end:
                return False
        
        return True
    except ValueError:
        # 日付形式が無効な場合は除外
        return False

def check_tester_filter(name, tester_filter, verbose_logger=None):
    """担当者フィルタをチェック"""
    if not name:
        return False
    
    target_name = tester_filter["value"].strip().lower()
    actual_name = name.strip().lower()
    exact_match = tester_filter["exact_match"]
    
    if exact_match:
        return actual_name == target_name
    else:
        return target_name in actual_name

def check_result_type_filter(result, result_types, verbose_logger=None):
    """結果タイプフィルタをチェック"""
    if not result:
        return False
    
    return result in result_types

def check_environment_filter(name, environment_filter, verbose_logger=None):
    """環境フィルタをチェック"""
    if not name:
        return False
    
    target_env = environment_filter["value"].strip().lower()
    actual_name = name.strip().lower()
    exact_match = environment_filter["exact_match"]
    
    if exact_match:
        return actual_name == target_env
    else:
        return target_env in actual_name
