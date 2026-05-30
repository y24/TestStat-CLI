import csv
import json
import os
from datetime import datetime

class OutputWriter:
    """CSV/Excel形式での出力を担当するクラス"""
    
    def __init__(self, verbose_logger=None):
        self.verbose_logger = verbose_logger
    
    def write_csv(self, data, output_file, is_multiple_files=False, settings=None):
        """CSV形式でファイルに出力"""
        try:
            # 出力ディレクトリの確認・作成
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                if self.verbose_logger:
                    self.verbose_logger.log(f"出力ディレクトリを作成しました: {output_dir}")
            
            # ファイルが既に存在する場合の確認
            if os.path.exists(output_file):
                if self.verbose_logger:
                    self.verbose_logger.log(f"既存ファイルを上書きします: {output_file}")
            
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                if is_multiple_files:
                    self._write_multiple_files_csv(data, csvfile, settings)
                else:
                    self._write_single_file_csv(data, csvfile, settings)
            
            if self.verbose_logger:
                self.verbose_logger.log(f"CSVファイルを出力しました: {output_file}")
            
            return True, None
            
        except PermissionError:
            error_msg = f"ファイルの書き込み権限がありません: {output_file}"
            if self.verbose_logger:
                self.verbose_logger.log(f"ERROR: {error_msg}")
            return False, error_msg
        except OSError as e:
            error_msg = f"ファイル出力エラー: {output_file}, 詳細: {e}"
            if self.verbose_logger:
                self.verbose_logger.log(f"ERROR: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"予期しないエラーが発生しました: {e}"
            if self.verbose_logger:
                self.verbose_logger.log(f"ERROR: {error_msg}")
            return False, error_msg
    
    def _write_single_file_csv(self, data, csvfile, settings=None):
        """単一ファイルのCSV出力"""
        writer = csv.writer(csvfile)
        use_plan_row = settings.get("output_definition", {}).get("use_plan_row", False) if settings else False
        
        # TOTAL RESULTS
        if "total" in data:
            writer.writerow(["Category", "Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A", "未実施", "Total", "完了数", "消化数", "完了率(%)", "消化率(%)"])
            total = data["total"]
            writer.writerow([
                "TOTAL RESULTS",
                total.get("Pass", 0),
                total.get("Fixed", 0),
                total.get("Fail", 0),
                total.get("Blocked", 0),
                total.get("Suspend", 0),
                total.get("N/A", 0),
                total.get("未実施", 0),
                total.get("Total", 0),
                total.get("完了数", 0),
                total.get("消化数", 0),
                total.get("完了率(%)", 0),
                total.get("消化率(%)", 0)
            ])
            writer.writerow([])  # 空行
        
        # STATISTICS
        if "stats" in data:
            writer.writerow(["Metric", "Count"])
            stats = data["stats"]
            for metric in ["all", "available", "executed", "completed", "incompleted", "planned"]:
                if metric in stats:
                    writer.writerow([metric.capitalize(), stats[metric]])
            writer.writerow([])  # 空行
        
        # DAILY BREAKDOWN
        if "daily" in data:
            headers = ["Date", "Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A", "完了数", "消化数"]
            if use_plan_row:
                headers.append("計画数")
            writer.writerow(headers)
            for date, daily_data in sorted(data["daily"].items()):
                row = [
                    date,
                    daily_data.get("Pass", 0),
                    daily_data.get("Fixed", 0),
                    daily_data.get("Fail", 0),
                    daily_data.get("Blocked", 0),
                    daily_data.get("Suspend", 0),
                    daily_data.get("N/A", 0),
                    daily_data.get("完了数", 0),
                    daily_data.get("消化数", 0)
                ]
                if use_plan_row:
                    row.append(daily_data.get("計画数", 0))
                writer.writerow(row)
            writer.writerow([])  # 空行
        
        # BY NAME
        if "by_name" in data:
            # 担当者名を取得
            testers = set()
            for daily_data in data["by_name"].values():
                testers.update(daily_data.keys())
            testers = sorted([a for a in testers if a not in ["完了数", "消化数", "計画数"]])
            
            if testers:
                headers = ["Date"] + testers
                writer.writerow(headers)
                for date, name_data in sorted(data["by_name"].items()):
                    row = [date]
                    for tester in testers:
                        row.append(name_data.get(tester, 0))
                    writer.writerow(row)
                writer.writerow([])  # 空行
        
        # BY ENVIRONMENT
        if "by_env" in data:
            headers = ["Environment", "Date", "Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A", "完了数", "消化数"]
            if use_plan_row:
                headers.append("計画数")
            writer.writerow(headers)
            for env_name, env_data in sorted(data["by_env"].items()):
                for date, env_stats in sorted(env_data.items()):
                    row = [
                        env_name,
                        date,
                        env_stats.get("Pass", 0),
                        env_stats.get("Fixed", 0),
                        env_stats.get("Fail", 0),
                        env_stats.get("Blocked", 0),
                        env_stats.get("Suspend", 0),
                        env_stats.get("N/A", 0),
                        env_stats.get("完了数", 0),
                        env_stats.get("消化数", 0)
                    ]
                    if use_plan_row:
                        row.append(env_stats.get("計画数", 0))
                    writer.writerow(row)
    
    def _write_multiple_files_csv(self, data, csvfile, settings=None):
        """複数ファイルのCSV出力"""
        writer = csv.writer(csvfile)
        use_plan_row = settings.get("output_definition", {}).get("use_plan_row", False) if settings else False
        
        # TOTAL RESULTS
        if "summary" in data and "total_results" in data["summary"]:
            writer.writerow(["Category", "Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A", "未実施", "Total", "完了数", "消化数", "完了率(%)", "消化率(%)"])
            total = data["summary"]["total_results"]
            writer.writerow([
                "TOTAL RESULTS",
                total.get("Pass", 0),
                total.get("Fixed", 0),
                total.get("Fail", 0),
                total.get("Blocked", 0),
                total.get("Suspend", 0),
                total.get("N/A", 0),
                total.get("未実施", 0),
                total.get("Total", 0),
                total.get("完了数", 0),
                total.get("消化数", 0),
                total.get("完了率(%)", 0),
                total.get("消化率(%)", 0)
            ])
            writer.writerow([])  # 空行
        
        # SUMMARY STATISTICS
        if "summary" in data and "total_stats" in data["summary"]:
            writer.writerow(["Metric", "Total"])
            stats = data["summary"]["total_stats"]
            for metric in ["all", "available", "executed", "completed", "incompleted", "planned"]:
                if metric in stats:
                    writer.writerow([f"{metric.capitalize()} Cases", stats[metric]])
            writer.writerow([])  # 空行
        
        # INDIVIDUAL FILES
        if "files" in data:
            writer.writerow(["File", "Total Cases", "Available Cases", "Excluded Cases", "Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A", "Total", "完了数", "消化数", "完了率(%)", "消化率(%)", "Start Date", "Latest Update"])
            for file_data in data["files"]:
                if "total" in file_data and "stats" in file_data:
                    total = file_data["total"]
                    stats = file_data["stats"]
                    run_info = file_data.get("run", {})
                    writer.writerow([
                        file_data.get("file", ""),
                        stats.get("all", 0),
                        stats.get("available", 0),
                        stats.get("excluded", 0),
                        total.get("Pass", 0),
                        total.get("Fixed", 0),
                        total.get("Fail", 0),
                        total.get("Blocked", 0),
                        total.get("Suspend", 0),
                        total.get("N/A", 0),
                        total.get("Total", 0),
                        total.get("完了数", 0),
                        total.get("消化数", 0),
                        total.get("完了率(%)", 0),
                        total.get("消化率(%)", 0),
                        run_info.get("start_date") or "-",
                        run_info.get("last_update") or "-"
                    ])
            writer.writerow([])  # 空行
        
        # BY NAME
        if "files" in data:
            # 全ファイルの担当者別データを統合
            combined_by_name = {}
            for file_data in data["files"]:
                if "by_name" in file_data:
                    for date, name_data in file_data["by_name"].items():
                        if date not in combined_by_name:
                            combined_by_name[date] = {}
                        for name, count in name_data.items():
                            if name not in combined_by_name[date]:
                                combined_by_name[date][name] = 0
                            combined_by_name[date][name] += count
            
            # 担当者名を取得
            testers = set()
            for daily_data in combined_by_name.values():
                testers.update(daily_data.keys())
            testers = sorted([a for a in testers if a not in ["完了数", "消化数", "計画数"]])
            
            if testers:
                headers = ["Date"] + testers
                writer.writerow(headers)
                for date, name_data in sorted(combined_by_name.items()):
                    row = [date]
                    for tester in testers:
                        row.append(name_data.get(tester, 0))
                    writer.writerow(row)
                writer.writerow([])  # 空行
        
        # BY ENVIRONMENT
        if "by_env" in data:
            headers = ["Environment", "Date", "Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A", "完了数", "消化数"]
            if use_plan_row:
                headers.append("計画数")
            writer.writerow(headers)
            for env_name, env_data in sorted(data["by_env"].items()):
                for date, env_stats in sorted(env_data.items()):
                    row = [
                        env_name,
                        date,
                        env_stats.get("Pass", 0),
                        env_stats.get("Fixed", 0),
                        env_stats.get("Fail", 0),
                        env_stats.get("Blocked", 0),
                        env_stats.get("Suspend", 0),
                        env_stats.get("N/A", 0),
                        env_stats.get("完了数", 0),
                        env_stats.get("消化数", 0)
                    ]
                    if use_plan_row:
                        row.append(env_stats.get("計画数", 0))
                    writer.writerow(row)
    
    