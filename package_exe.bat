@echo off
chcp 65001 > nul
echo TestStat-CLI 配布パッケージ作成スクリプト
echo ===========================================

REM exeファイルのビルド
echo exeファイルをビルドしています...
python build_exe.py build

if %ERRORLEVEL% NEQ 0 (
    echo ビルドに失敗しました。
    pause
    exit /b 1
)

REM 配布パッケージの作成
echo.
echo 配布パッケージを作成しています...
python package_exe.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===========================================
    echo 配布パッケージの作成が完了しました！
    echo.
    echo 作成されたファイル:
    echo   - dist_package/  (配布用フォルダ)
    echo   - TestStat-CLI_v1.0.0_*.zip  (ZIPパッケージ)
    echo.
    echo 使用方法:
    echo   1. dist_packageフォルダを配布
    echo   2. またはZIPファイルを配布
    echo.
) else (
    echo.
    echo パッケージ作成に失敗しました。
    echo エラーメッセージを確認してください。
    echo.
)

pause 