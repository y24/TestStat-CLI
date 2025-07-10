from logging import getLogger, StreamHandler, FileHandler, Formatter, ERROR, WARNING, INFO, DEBUG

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