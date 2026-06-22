@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs

if /I "%~1"=="api" goto api

if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -m scripts.collect_labels >> logs\collect_%date:~0,4%%date:~5,2%%date:~8,2%.log 2>&1
exit /b %ERRORLEVEL%

:api
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Method POST -Uri http://localhost:18000/api/v1/collect -UseBasicParsing" >> logs\collect_%date:~0,4%%date:~5,2%%date:~8,2%.log 2>&1
exit /b %ERRORLEVEL%
