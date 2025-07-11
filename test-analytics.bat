@echo off
chcp 65001 >nul
REM TestSpecAnalyticsCLI - シンプルコマンド実行用バッチファイル
REM 使用方法: test-analytics [オプション] [ファイルパス/フォルダパス]

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM Python環境の確認
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Pythonがインストールされていません。
    echo Python 3.7以上をインストールしてください。
    pause
    exit /b 1
)

REM 仮想環境の確認とアクティベート
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo WARNING: 仮想環境が見つかりません。システムのPythonを使用します。
)

REM 依存関係の確認
python -c "import openpyxl, pyperclip" >nul 2>&1
if errorlevel 1 (
    echo ERROR: 必要なライブラリがインストールされていません。
    echo 以下のコマンドでインストールしてください：
    echo pip install -r requirements.txt
    pause
    exit /b 1
)

REM メインスクリプトの実行
python test_spec_analytics.py %*

REM エラーコードを保持
set EXIT_CODE=%errorlevel%

REM 仮想環境を非アクティブ化
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\deactivate.bat"
)

exit /b %EXIT_CODE% 