import pyperclip
import traceback
from utils import DataConversion
from utils import Logger

logger = Logger.get_logger(__name__, console=True, file=False, trace_line=False)

class ClipboardWriter:
    """TSVクリップボード出力機能を提供するクラス"""
    
    def __init__(self, verbose_logger=None):
        """
        ClipboardWriterの初期化
        
        Args:
            verbose_logger: 詳細ログ用のロガー
        """
        self.verbose_logger = verbose_logger
    
    def write_to_clipboard(self, data, settings):
        """
        TSV形式でクリップボードにデータをコピーする
        
        Args:
            data: 集計データのリスト
            settings: 設定情報
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            if self.verbose_logger:
                self.verbose_logger.log("TSVデータ変換開始")
            
            # DataConversion.pyのconvert_to_2d_array関数を使用してTSVデータを生成
            tsv_data = DataConversion.convert_to_2d_array(data, settings)
            
            if self.verbose_logger:
                self.verbose_logger.log(f"変換データ行数: {len(tsv_data)}行")
            
            # TSV形式の文字列に変換
            tsv_string = self._convert_to_tsv_string(tsv_data)
            
            if self.verbose_logger:
                self.verbose_logger.log("クリップボードコピー開始")
            
            # クリップボードにコピー
            pyperclip.copy(tsv_string)
            
            if self.verbose_logger:
                data_size = len(tsv_string.encode('utf-8'))
                size_kb = data_size / 1024
                self.verbose_logger.log(f"クリップボードコピー完了 - データサイズ: {size_kb:.1f}KB")
            
            return True
            
        except pyperclip.PyperclipException as e:
            error_msg = f"クリップボードアクセスエラー: {str(e)}"
            logger.error(error_msg)
            if self.verbose_logger:
                self.verbose_logger.log_error_details("clipboard_access_error", error_msg)
            return False
            
        except Exception as e:
            error_msg = f"クリップボードコピー中にエラーが発生しました: {str(e)}"
            logger.error(error_msg)
            if self.verbose_logger:
                self.verbose_logger.log_error_details("clipboard_copy_error", error_msg)
            return False
    
    def _convert_to_tsv_string(self, tsv_data):
        """
        2次元配列をTSV形式の文字列に変換する
        
        Args:
            tsv_data: 2次元配列のデータ
            
        Returns:
            str: TSV形式の文字列
        """
        tsv_lines = []
        
        for row in tsv_data:
            # 各セルの値をTSV形式に変換（タブ文字で区切り）
            tsv_row = []
            for cell in row:
                # セルの値を文字列に変換し、タブ文字や改行文字をエスケープ
                cell_str = str(cell) if cell is not None else ""
                # タブ文字をスペースに置換（TSVではタブが区切り文字のため）
                cell_str = cell_str.replace('\t', ' ')
                # 改行文字をスペースに置換
                cell_str = cell_str.replace('\n', ' ')
                cell_str = cell_str.replace('\r', ' ')
                tsv_row.append(cell_str)
            
            # タブ文字で結合
            tsv_line = '\t'.join(tsv_row)
            tsv_lines.append(tsv_line)
        
        # 改行文字で結合
        return '\n'.join(tsv_lines)
    
    def write_to_console_as_fallback(self, data, settings):
        """
        クリップボードコピーが失敗した場合のフォールバック機能
        コンソールにTSVデータを出力する
        
        Args:
            data: 集計データのリスト
            settings: 設定情報
        """
        try:
            tsv_data = DataConversion.convert_to_2d_array(data, settings)
            tsv_string = self._convert_to_tsv_string(tsv_data)
            
            print("\n" + "="*50)
            print("TSV DATA (クリップボードコピーに失敗したため、コンソールに出力)")
            print("="*50)
            print(tsv_string)
            print("="*50)
            print("上記のデータをコピーしてExcelに貼り付けてください。")
            print("="*50 + "\n")
            
        except Exception as e:
            error_msg = f"フォールバック出力中にエラーが発生しました: {str(e)}"
            logger.error(error_msg)
            if self.verbose_logger:
                self.verbose_logger.log_error_details("fallback_output_error", error_msg) 