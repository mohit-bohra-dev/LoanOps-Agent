@echo off
title LoanOps Agent Servicing Agent Demo Controller

echo ================================================
echo LoanOps Agent Servicing Agent Demo Controller
echo ================================================

echo Stopping any existing demo services...
taskkill /F /FI "WINDOWTITLE eq *uvicorn*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq *vite*" >nul 2>&1

echo Waiting for ports to be released...
ping 127.0.0.1 -n 4 >nul

echo Starting Tools API on port 8001...
start "Tools API" /min cmd /c "cd /d %cd% && uv run uvicorn apps.tools_api.main:app --port 8001"

echo Waiting for Tools API to start...
ping 127.0.0.1 -n 4 >nul

echo Starting Agent API on port 8000...
start "Agent API" /min cmd /c "cd /d %cd% && uv run uvicorn apps.agent_api.main:app --port 8000"

echo Waiting for Agent API to start...
ping 127.0.0.1 -n 4 >nul

echo Starting Web UI on port 5173...
start "Web UI" /min cmd /c "cd /d %cd%\apps\web_ui && npm run dev"

echo.
echo Demo services started successfully!
echo.
echo Access the application at:
echo   Web UI: http://localhost:5173
echo   Tools API Docs: http://localhost:8001/docs
echo   Agent API Health: http://localhost:8000/health
echo.
echo To stop the services, close the command windows or run stop-demo.bat
echo.
echo Press any key to exit this controller (services will continue running)...
pause >nul
