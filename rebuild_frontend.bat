@echo off
setlocal

echo ========================================
echo   TestStat Frontend Build
echo ========================================

set FRONTEND_ROOT=%~dp0teststat-frontend

if not exist "%FRONTEND_ROOT%" (
    echo Error: %FRONTEND_ROOT% directory not found.
    pause
    exit /b 1
)

echo.
echo Building for production...
pushd "%FRONTEND_ROOT%"
call npm run build
if %ERRORLEVEL% neq 0 (
    echo.
    echo Error: Build failed.
    popd
    pause
    exit /b 1
)
popd

echo.
echo ========================================
echo   Frontend Build Completed!
echo ========================================
pause
