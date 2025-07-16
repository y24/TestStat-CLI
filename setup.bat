@echo off
REM TestStatCLI - セットアップ用バッチファイル
REM 使用方法: setup.bat

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM 仮想環境がなければ作成
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM 仮想環境の有効化
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM 仮想環境が有効化されたか確認
echo [INFO] Checking Python path...
where python

REM 依存関係のインストール
echo [INFO] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

pause
