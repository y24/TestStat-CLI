#!/usr/bin/env python3
"""
TestStat-CLI exeビルドスクリプト
PyInstallerを使用してexeファイルを作成します
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """PyInstallerがインストールされているかチェック"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    """PyInstallerをインストール"""
    print("PyInstallerをインストールしています...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def create_spec_file():
    """PyInstallerのspecファイルを作成"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['test_stat_cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('assets/logo.txt', 'assets'),
        ('utils', 'utils'),
    ],
    hiddenimports=[
        'openpyxl',
        'pyperclip',
        'yaml',
        'utils.ReadData',
        'utils.Logger',
        'utils.OutputWriter',
        'utils.ClipboardWriter',
        'utils.DataConversion',
        'utils.Labels',
        'utils.Utility',
        'utils.OpenpyxlWrapper',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='tstat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('tstat.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("specファイルを作成しました: tstat.spec")

def build_exe():
    """exeファイルをビルド"""
    print("exeファイルをビルドしています...")
    
    # PyInstallerがインストールされているかチェック
    if not check_pyinstaller():
        install_pyinstaller()
    
    # specファイルを作成
    create_spec_file()
    
    # ビルド実行
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "tstat.spec"
    ])
    
    print("ビルドが完了しました！")
    print("実行ファイル: dist/tstat.exe")

def clean_build():
    """ビルドファイルをクリーンアップ"""
    print("ビルドファイルをクリーンアップしています...")
    
    # 削除対象のディレクトリとファイル
    cleanup_targets = [
        'build',
        'dist',
        '__pycache__',
        'tstat.spec'
    ]
    
    for target in cleanup_targets:
        if os.path.exists(target):
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            print(f"削除: {target}")
    
    print("クリーンアップが完了しました")

def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "clean":
            clean_build()
        elif command == "build":
            build_exe()
        else:
            print("使用方法:")
            print("  python build_exe.py build  - exeファイルをビルド")
            print("  python build_exe.py clean  - ビルドファイルをクリーンアップ")
    else:
        # デフォルトでビルド実行
        build_exe()

if __name__ == "__main__":
    main() 