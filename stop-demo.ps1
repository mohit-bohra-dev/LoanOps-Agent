# Stop LoanOps Agent stack (ports 8000, 8001, 5173)
# Usage: .\stop-demo.ps1

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Stop-PortListeners {
    param([int[]]$Ports)
    foreach ($port in $Ports) {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if (-not $conns) {
            Write-Host "Port $port: nothing listening" -ForegroundColor DarkGray
            continue
        }
        $procIds = $conns.OwningProcess | Select-Object -Unique
        foreach ($procId in $procIds) {
            if ($procId -and $procId -ne 0) {
                $name = "(unknown)"
                try { $name = (Get-Process -Id $procId -ErrorAction Stop).ProcessName } catch { }
                Write-Host "Stopping PID $procId ($name) on port $port..." -ForegroundColor Yellow
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Write-Host "Stopping demo services..." -ForegroundColor Yellow

# Prefer PIDs recorded by run-demo.ps1 (wrapper shells)
$pidFile = Join-Path $Root ".demo-pids.txt"
if (Test-Path $pidFile) {
    Get-Content $pidFile | ForEach-Object {
        if ($_ -match "=(?<id>\d+)$") {
            $procId = [int]$Matches["id"]
            Write-Host "Stopping wrapper PID $procId..." -ForegroundColor Yellow
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# Kill by listen port (actual uvicorn / vite children)
Stop-PortListeners -Ports @(8000, 8001, 5173)
Start-Sleep -Seconds 1

# Confirm
foreach ($port in @(8000, 8001, 5173)) {
    $still = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($still) {
        Write-Host "WARNING: port $port still in use" -ForegroundColor Red
    } else {
        Write-Host "Port $port free" -ForegroundColor Green
    }
}

Write-Host "Done." -ForegroundColor Green
