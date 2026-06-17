# Stop all demo services
# This script stops all running demo services

Write-Host "Stopping all demo services..." -ForegroundColor Yellow

# Kill uvicorn processes
$uvicornProcesses = Get-Process -Name "*python*" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" }
foreach ($process in $uvicornProcesses) {
    Write-Host "Stopping uvicorn process (PID: $($process.Id))..." -ForegroundColor Yellow
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
}

# Kill vite processes
$viteProcesses = Get-Process -Name "*node*" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vite*" }
foreach ($process in $viteProcesses) {
    Write-Host "Stopping vite process (PID: $($process.Id))..." -ForegroundColor Yellow
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
}

# Alternative method using taskkill
Write-Host "Using taskkill as fallback..." -ForegroundColor Yellow
taskkill /F /FI "WINDOWTITLE eq *uvicorn*" 2>$null
taskkill /F /FI "WINDOWTITLE eq *vite*" 2>$null

Write-Host "All demo services stopped." -ForegroundColor Green
