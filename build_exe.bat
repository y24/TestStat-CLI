@echo off
chcp 65001 > nul
echo TestStat-CLI exeビルドスクリプト
echo =================================

REM 仮想環境のアクティベート（存在する場合）
if exist .venv\Scripts\activate.bat (
    echo 仮想環境をアクティベートしています...
    call .venv\Scripts\activate.bat
)

REM 必要なパッケージのインストール
echo 必要なパッケージをインストールしています...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

REM exeファイルのビルド
echo.
echo exeファイルをビルドしています...
python build_exe.py build

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =================================
    echo ビルドが完了しました！
    echo 実行ファイル: dist\tstat.exe
    echo.
    echo 使用方法:
    echo   dist\tstat.exe --help
    echo.
) else (
    echo.
    echo ビルドに失敗しました。
    echo エラーメッセージを確認してください。
    echo.
)

pause 