@echo off
title LoanOps Agent Servicing Agent Demo Stopper

echo ================================================
echo LoanOps Agent Servicing Agent Demo Stopper
echo ================================================

echo Stopping all demo services...
echo.

echo Stopping uvicorn processes...
taskkill /F /FI "WINDOWTITLE eq *uvicorn*" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   - Uvicorn processes stopped
) else (
    echo   - No uvicorn processes found
)

echo Stopping vite processes...
taskkill /F /FI "WINDOWTITLE eq *vite*" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   - Vite processes stopped
) else (
    echo   - No vite processes found
)

echo.
echo All demo services stopped.
echo.
pause
