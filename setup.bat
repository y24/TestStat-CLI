@echo off
REM TestStatCLI - Setup batch file
REM Usage: setup.bat

REM Move to the script directory
cd /d "%~dp0"

REM Create virtual environment if it does not exist
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Check if virtual environment is activated
echo [INFO] Checking Python path...
where python

REM Install dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo [SUCCESS] Setup completed successfully.
pause
