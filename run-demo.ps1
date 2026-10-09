# Start LoanOps Agent stack: MCP :8001, Agent API :8000, Web UI :5173
# Usage: .\run-demo.ps1
# Stop:  .\stop-demo.ps1
# Note: apps/tools_api was removed (ADR-010); :8001 is packages.mcp_server.

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Stop-PortListeners {
    param([int[]]$Ports)
    foreach ($port in $Ports) {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if (-not $conns) { continue }
        $procIds = $conns.OwningProcess | Select-Object -Unique
        foreach ($procId in $procIds) {
            if ($procId -and $procId -ne 0) {
                Write-Host "Stopping PID $procId on port $port..." -ForegroundColor Yellow
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Write-Host "Stopping anything already on 8000/8001/5173..." -ForegroundColor Yellow
Stop-PortListeners -Ports @(8000, 8001, 5173)
Start-Sleep -Seconds 2

$pidFile = Join-Path $Root ".demo-pids.txt"
if (Test-Path $pidFile) { Remove-Item $pidFile -Force }

# Force registry + local fixtures for SC-010 (does not edit user .env; child env only).
$demoEnv = @(
    "`$env:SSE__CATALOG_SOURCE='registry'"
    "`$env:EAKG__ENVIRONMENT='local'"
    "`$env:SSE__USE_FIXTURE='true'"
) -join "; "

Write-Host "Starting MCP server on :8001 (registry/local)..." -ForegroundColor Green
$mcp = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoProfile", "-Command",
    "$demoEnv; Set-Location '$Root'; uv run python -m packages.mcp_server"
) -PassThru -WindowStyle Minimized

Write-Host "Starting Agent API on :8000..." -ForegroundColor Green
$agent = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoProfile", "-Command",
    "$demoEnv; Set-Location '$Root'; uv run uvicorn apps.agent_api.main:app --host 127.0.0.1 --port 8000"
) -PassThru -WindowStyle Minimized

Write-Host "Starting Web UI on :5173..." -ForegroundColor Green
$web = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoProfile", "-Command",
    "Set-Location '$Root\apps\web_ui'; npm run dev"
) -PassThru -WindowStyle Minimized

@(
    "mcp=$($mcp.Id)"
    "agent=$($agent.Id)"
    "web=$($web.Id)"
) | Set-Content -Path $pidFile -Encoding ASCII

Write-Host "Waiting for health checks..." -ForegroundColor Yellow
$deadline = (Get-Date).AddSeconds(90)
$mcpOk = $false
$agentOk = $false
$webOk = $false
while ((Get-Date) -lt $deadline) {
    if (-not $mcpOk) {
        try {
            $null = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -UseBasicParsing -TimeoutSec 2
            $mcpOk = $true
        } catch { }
    }
    if (-not $agentOk) {
        try {
            $null = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2
            $agentOk = $true
        } catch { }
    }
    if (-not $webOk) {
        try {
            $null = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -UseBasicParsing -TimeoutSec 2
            $webOk = $true
        } catch { }
    }
    if ($mcpOk -and $agentOk -and $webOk) { break }
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "Status:" -ForegroundColor Cyan
Write-Host ("  MCP server :8001  " + $(if ($mcpOk) { "UP" } else { "starting..." }))
Write-Host ("  Agent API  :8000  " + $(if ($agentOk) { "UP" } else { "starting..." }))
Write-Host ("  Web UI     :5173  " + $(if ($webOk) { "UP" } else { "starting..." }))
Write-Host ""
Write-Host "URLs:" -ForegroundColor Cyan
Write-Host "  Web UI:            http://localhost:5173"
Write-Host "  Agent API health:  http://localhost:8000/health"
Write-Host "  MCP health:        http://localhost:8001/health"
Write-Host "  MCP ready:         http://localhost:8001/ready"
Write-Host "  MCP endpoint:      http://localhost:8001/mcp"
Write-Host ""
Write-Host "Stop with: .\stop-demo.ps1" -ForegroundColor Yellow

if (-not ($mcpOk -and $agentOk -and $webOk)) {
    exit 1
}
