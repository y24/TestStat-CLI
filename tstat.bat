@echo off
REM TestStatCLI - Simple command execution batch file
REM Usage: tstat [options] [file path/folder path]

REM Move to the script directory
cd /d "%~dp0"

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Run main script
echo [INFO] Running Application...
python test_stat_cli.py %*

REM Store error code
set EXIT_CODE=%errorlevel%

REM Deactivate virtual environment
deactivate

exit /b %EXIT_CODE% 