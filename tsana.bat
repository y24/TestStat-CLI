@echo off
REM TestSpecAnalyticsCLI - シンプルコマンド実行用バッチファイル
REM 使用方法: test-analytics [オプション] [ファイルパス/フォルダパス]

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM 仮想環境の有効化
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM メインスクリプトの実行
echo [INFO] Running Application...
python test_spec_analytics.py %*

REM エラーコードを保持
set EXIT_CODE=%errorlevel%

REM 仮想環境の無効化
deactivate

exit /b %EXIT_CODE% 