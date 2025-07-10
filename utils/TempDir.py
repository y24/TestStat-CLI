import tempfile
import os
import shutil
import glob

def cleanup_old_temp_dirs(dir_prefix):
    """
    スクリプトの起動時に、過去の一時フォルダを削除する。
    """
    temp_base_dir = tempfile.gettempdir()
    temp_dirs = glob.glob(os.path.join(temp_base_dir, dir_prefix + "*"))

    for temp_dir in temp_dirs:
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)

def cleanup_temp_dir(temp_dir):
    """
    指定された一時フォルダを削除する。

    :param temp_dir: 削除する一時フォルダのパス
    """
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
