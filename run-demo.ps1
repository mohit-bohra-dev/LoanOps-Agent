# Run the LoanOps Agent Servicing Agent Demo
# This script starts all three services in the background with proper delays

Write-Host "Stopping any existing demo services..." -ForegroundColor Yellow
taskkill /F /FI "WINDOWTITLE eq *uvicorn*" 2>$null
taskkill /F /FI "WINDOWTITLE eq *vite*" 2>$null

Write-Host "Waiting for ports to be released..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "Starting Tools API on port 8001..." -ForegroundColor Green
Start-Process PowerShell -ArgumentList "-Command", "cd '$pwd'; uv run uvicorn apps.tools_api.main:app --port 8001" -WindowStyle Minimized

Write-Host "Waiting for Tools API to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "Starting Agent API on port 8000..." -ForegroundColor Green
Start-Process PowerShell -ArgumentList "-Command", "cd '$pwd'; uv run uvicorn apps.agent_api.main:app --port 8000" -WindowStyle Minimized

Write-Host "Waiting for Agent API to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "Starting Web UI on port 5173..." -ForegroundColor Green
Start-Process PowerShell -ArgumentList "-Command", "cd '$pwd/apps/web_ui'; npm run dev" -WindowStyle Minimized

Write-Host ""
Write-Host "Demo services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Access the application at:" -ForegroundColor Cyan
Write-Host "  Web UI: http://localhost:5173" -ForegroundColor White
Write-Host "  Tools API Docs: http://localhost:8001/docs" -ForegroundColor White
Write-Host "  Agent API Health: http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "To stop the services, close the PowerShell windows or run:" -ForegroundColor Yellow
Write-Host "  .\stop-demo.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to exit this script (services will continue running)..."
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host "Script terminated."
}
