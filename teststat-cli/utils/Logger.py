from logging import getLogger, StreamHandler, FileHandler, Formatter, ERROR, WARNING, INFO, DEBUG
import time
import os
from datetime import datetime

# from modules import Logger
# logger = Logger.get_logger(__name__, console=True, file=False, trace_line=False)

# カスタムフォーマッター
class CustomFormatter(Formatter):
    # 色設定
    COLOR_MAP = {
        ERROR: "\033[91m",  # 赤
        WARNING: "\033[93m",  # 黄
        INFO: "\033[92m",  # 緑
        # DEBUG: "\033[94m",  # 青
        "RESET": "\033[0m",  # リセット
    }

    def format(self, record):
        color = self.COLOR_MAP.get(record.levelno, self.COLOR_MAP["RESET"])
        reset = self.COLOR_MAP["RESET"]
        message = super().format(record)
        return f"{color}{message}{reset}"

def get_logger(name:str, console=True, file=False, trace_line=False):
    """Loggerを作成する"""
    logger = getLogger(name)
    logger.setLevel(DEBUG)

    format = '%(asctime)s - %(levelname)s : %(name)s : %(message)s'
    if trace_line:
        format += ' (%(filename)s:%(lineno)d)'
    formatter = CustomFormatter(format)

    # コンソール出力
    if console:
        s_handler = StreamHandler()
        s_handler.setLevel(DEBUG)
        s_handler.setFormatter(formatter)
        logger.addHandler(s_handler)

    # ファイル出力
    if file:
        f_handler = FileHandler("./app.log")
        f_handler.setLevel(DEBUG)
        f_handler.setFormatter(formatter)
        logger.addHandler(f_handler)
    
    return logger

class VerboseLogger:
    """詳細ログ出力用クラス"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.start_time = None
        self.file_start_time = None
    
    def log(self, message):
        """詳細ログを出力"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[VERBOSE] {timestamp} - {message}")
    
    def start_file_processing(self, filepath):
        """ファイル処理開始"""
        if self.verbose:
            self.file_start_time = time.time()
            file_size = os.path.getsize(filepath) / 1024  # KB
            mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            self.log(f"ファイル処理開始: {filepath}")
            self.log(f"ファイルサイズ: {file_size:.1f} KB")
            self.log(f"最終更新日時: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def end_file_processing(self):
        """ファイル処理終了"""
        if self.verbose and self.file_start_time:
            elapsed = time.time() - self.file_start_time
            self.log(f"ファイル処理時間: {elapsed:.2f}秒")
    
    def start_processing(self):
        """全体処理開始"""
        if self.verbose:
            self.start_time = time.time()
            self.log("処理開始時刻: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def end_processing(self):
        """全体処理終了"""
        if self.verbose and self.start_time:
            elapsed = time.time() - self.start_time
            self.log(f"総処理時間: {elapsed:.2f}秒")
    
    def log_file_search(self, target_path, file_count):
        """ファイル検索結果"""
        if self.verbose:
            self.log(f"ファイル検索開始: {target_path}")
            self.log(f"検索対象パス: {target_path}")
            self.log(f"処理対象ファイル数: {file_count}")
    
    def log_excel_info(self, workbook, sheet_names):
        """Excelファイル情報"""
        if self.verbose:
            self.log("ワークブック情報:")
            self.log(f"- シート数: {len(workbook.sheetnames)}")
            self.log(f"- 使用シート: {', '.join(sheet_names)}")
    
    def log_data_range(self, header_row, data_start, data_end, total_rows):
        """データ範囲情報"""
        if self.verbose:
            self.log("データ読み取り範囲:")
            self.log(f"- ヘッダー行: {header_row}行目")
            self.log(f"- データ開始行: {data_start}行目")
            self.log(f"- データ終了行: {data_end}行目")
            self.log(f"- 総データ行数: {total_rows}行")
    
    def log_column_mapping(self, header, result_cols, person_cols, date_cols, plan_cols):
        """列マッピング情報"""
        if self.verbose:
            self.log("列マッピング:")
            if result_cols:
                self.log(f"- 結果列: {', '.join([chr(65 + col) + '列' for col in result_cols])}")
            if person_cols:
                self.log(f"- 担当者列: {', '.join([chr(65 + col) + '列' for col in person_cols])}")
            if date_cols:
                self.log(f"- 日付列: {', '.join([chr(65 + col) + '列' for col in date_cols])}")
            if plan_cols:
                self.log(f"- 計画列: {', '.join([chr(65 + col) + '列' for col in plan_cols])}")
    
    def log_data_validation(self, valid_dates, invalid_dates, persons, environments):
        """データ検証結果"""
        if self.verbose:
            self.log("データ検証結果:")
            self.log(f"- 有効な日付データ: {valid_dates}件")
            self.log(f"- 無効な日付データ: {invalid_dates}件")
            self.log(f"- 担当者データ: {len(persons)}名 ({', '.join(persons)})")
            self.log(f"- 環境データ: {len(environments)}環境 ({', '.join(environments)})")
    
    def log_result_summary(self, results, total_count):
        """結果タイプ別集計"""
        if self.verbose:
            self.log("結果タイプ別集計:")
            for result_type, count in results.items():
                if count > 0:
                    percentage = (count / total_count * 100) if total_count > 0 else 0
                    self.log(f"- {result_type}: {count}件 ({percentage:.1f}%)")
    
    def log_daily_breakdown(self, daily_data):
        """日別データ処理"""
        if self.verbose:
            self.log("日別データ処理:")
            for date, data in sorted(daily_data.items()):
                result_summary = []
                for result_type, count in data.items():
                    if count > 0 and result_type not in ['完了数', '消化数', '計画数']:
                        result_summary.append(f"{result_type}:{count}")
                if result_summary:
                    self.log(f"- {date}: {sum(data.values())}件 ({', '.join(result_summary)})")
    
    def log_person_summary(self, person_data):
        """担当者別集計"""
        if self.verbose:
            self.log("担当者別集計:")
            for person, count in sorted(person_data.items()):
                self.log(f"- {person}: {count}件")
    
    def log_environment_summary(self, env_data):
        """環境別集計"""
        if self.verbose:
            self.log("環境別集計:")
            for env, data in sorted(env_data.items()):
                # 環境別データは{日付: {結果タイプ: 数値}}の構造
                total = 0
                for date_data in data.values():
                    if isinstance(date_data, dict):
                        total += sum(date_data.values())
                    else:
                        total += date_data
                self.log(f"- {env}: {total}件")
    
    def log_warning(self, message):
        """警告メッセージ"""
        if self.verbose:
            self.log(f"警告: {message}")
    
    def log_error_details(self, error_type, message, details=None):
        """エラー詳細情報"""
        if self.verbose:
            self.log(f"エラー詳細情報:")
            self.log(f"- エラー種別: {error_type}")
            self.log(f"- エラー内容: {message}")
            if details:
                self.log(f"- 詳細: {details}")
    
    def log_performance(self, operation, elapsed_time):
        """パフォーマンス情報"""
        if self.verbose:
            self.log(f"{operation}時間: {elapsed_time:.2f}秒")