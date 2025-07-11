@echo off
REM TestSpecAnalyticsCLI - シンプルコマンド実行用バッチファイル
REM 使用方法: test-analytics [オプション] [ファイルパス/フォルダパス]

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM 仮想環境がなければ作成
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

REM 仮想環境の有効化
call .venv\Scripts\activate.bat

REM 依存関係のインストール
REM pip install -r requirements.txt

REM 依存関係の確認
python -c "import openpyxl, pyperclip, yaml" >nul 2>&1
if errorlevel 1 (
    echo ERROR: 必要なライブラリがインストールされていません。
    echo コマンドプロンプトで次を実行してください:
    echo pip install -r requirements.txt
    pause
    exit /b 1
)

REM メインスクリプトの実行
python test_spec_analytics.py %*

REM エラーコードを保持
set EXIT_CODE=%errorlevel%

REM 仮想環境の無効化
deactivate

exit /b %EXIT_CODE% 