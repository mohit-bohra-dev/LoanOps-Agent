#Requires -Version 5.1
<#
.SYNOPSIS
  Start local LoanOps stack: SSO, SSE M2M, GraphDB, MCP, Agent API, Web UI.

.DESCRIPTION
  Idempotent-ish: skips ports already listening. Never prints tokens.

  From repo root:
    .\scripts\dev\start-stack.ps1
    .\scripts\dev\start-stack.ps1 -SkipSso -SkipM2m
    .\scripts\dev\start-stack.ps1 -RefreshIndex
    .\scripts\dev\start-stack.ps1 -NoUi

.NOTES
  GraphDB helper: D:\Users\v-mbohra\tools\start-graphdb.cmd (override -GraphDbStartCmd)
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$AwsProfile = "dev",
    [string]$GraphDbStartCmd = "D:\Users\v-mbohra\tools\start-graphdb.cmd",
    [string]$M2mProbeUrl = "https://loanservicesapi.dev.pennymac.plaisse.com/api/Loans/1000002245/Summary",
    [switch]$SkipSso,
    [switch]$SkipM2m,
    [switch]$SkipGraphDb,
    [switch]$SkipMcp,
    [switch]$SkipAgent,
    [switch]$NoUi,
    [switch]$RefreshIndex,
    [int]$WaitTimeoutSec = 120
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

function Test-PortOpen([int]$Port) {
    try {
        return (Test-NetConnection -ComputerName "127.0.0.1" -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded
    }
    catch {
        return $false
    }
}

function Start-LoggedProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$LogName
    )
    $logDir = Join-Path $RepoRoot "out\stack-logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $outLog = Join-Path $logDir "$LogName.out.log"
    $errLog = Join-Path $logDir "$LogName.err.log"
    $env:AWS_PROFILE = $AwsProfile
    $p = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList `
        -WorkingDirectory $RepoRoot -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    Write-Output "  started $Name pid=$($p.Id) logs=$logDir\$LogName.*.log"
    return $p
}

Write-Output "=== LoanOps start-stack (root=$RepoRoot profile=$AwsProfile) ==="

# 1) SSO
if (-not $SkipSso) {
    Write-Output "[1/7] aws sso login --profile $AwsProfile"
    aws sso login --profile $AwsProfile
    if ($LASTEXITCODE -ne 0) { throw "aws sso login failed" }
    $env:AWS_PROFILE = $AwsProfile
}
else {
    Write-Output "[1/7] SSO skipped"
    $env:AWS_PROFILE = $AwsProfile
}

# 2) M2M -> SSE__API_KEY
if (-not $SkipM2m) {
    Write-Output "[2/7] refresh SSE M2M"
    & (Join-Path $RepoRoot "scripts\auth\refresh-sse-m2m.ps1") -LoanOpsRoot $RepoRoot -ProbeUrl $M2mProbeUrl
    if (-not $?) { throw "refresh-sse-m2m.ps1 failed" }
}
else {
    Write-Output "[2/7] M2M skipped"
}

# 3) GraphDB
if (-not $SkipGraphDb) {
    if (Test-PortOpen 7200) {
        Write-Output "[3/7] GraphDB already on :7200"
    }
    elseif (Test-Path $GraphDbStartCmd) {
        Write-Output "[3/7] starting GraphDB via $GraphDbStartCmd"
        cmd /c "`"$GraphDbStartCmd`""
    }
    else {
        Write-Warning "[3/7] GraphDB start cmd missing: $GraphDbStartCmd (SPARQL/EAKG will be down)"
    }
}
else {
    Write-Output "[3/7] GraphDB skipped"
}

# 4) MCP :8001 — restart if up so .env M2M reloads
$uv = (Get-Command uv -ErrorAction Stop).Source
if (-not $SkipMcp) {
    if (Test-PortOpen 8001) {
        Write-Output "[4/7] MCP :8001 up — recycling to load .env"
        Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 1
    }
    else {
        Write-Output "[4/7] starting MCP :8001"
    }
    Start-LoggedProcess -Name "mcp" -FilePath $uv -ArgumentList @("run", "python", "-m", "packages.mcp_server") -LogName "mcp" | Out-Null
}
else {
    Write-Output "[4/7] MCP skipped"
}

# 5) Agent API :8000
if (-not $SkipAgent) {
    if (Test-PortOpen 8000) {
        Write-Output "[5/7] Agent API already on :8000"
    }
    else {
        Write-Output "[5/7] starting Agent API :8000"
        Start-LoggedProcess -Name "agent" -FilePath $uv `
            -ArgumentList @("run", "uvicorn", "apps.agent_api.main:app", "--host", "127.0.0.1", "--port", "8000") `
            -LogName "agent" | Out-Null
    }
}
else {
    Write-Output "[5/7] Agent skipped"
}

# 6) Web UI
if (-not $NoUi) {
    if (Test-PortOpen 5173) {
        Write-Output "[6/7] Web UI already on :5173"
    }
    else {
        Write-Output "[6/7] starting Vite :5173"
        $npm = (Get-Command npm -ErrorAction Stop).Source
        Start-LoggedProcess -Name "web_ui" -FilePath $npm `
            -ArgumentList @("--prefix", "apps/web_ui", "run", "dev") `
            -LogName "web_ui" | Out-Null
    }
}
else {
    Write-Output "[6/7] UI skipped"
}

# 7) Optional ApiIndex refresh
if ($RefreshIndex) {
    Write-Output "[7/7] ApiIndex refresh (may take minutes)"
    & $uv run python (Join-Path $RepoRoot "scripts\dev\stack_ops.py") refresh-index --env dev
}
else {
    Write-Output "[7/7] ApiIndex refresh skipped (pass -RefreshIndex)"
}

Write-Output "Waiting for ports (timeout ${WaitTimeoutSec}s)..."
& $uv run python (Join-Path $RepoRoot "scripts\dev\stack_ops.py") wait --timeout $WaitTimeoutSec `
    --services postgres graphdb mcp agent_api
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Some core ports not ready — run: uv run python scripts/dev/stack_ops.py status"
}

Write-Output ""
Write-Output "=== status ==="
& $uv run python (Join-Path $RepoRoot "scripts\dev\stack_ops.py") status
Write-Output ""
Write-Output "UI http://localhost:5173/  Agent http://127.0.0.1:8000/health  GraphDB http://localhost:7200/"
Write-Output "Stop: .\scripts\dev\stop-stack.ps1"
