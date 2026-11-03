#Requires -Version 5.1
<#
.SYNOPSIS
  Stop LoanOps local stack processes bound to known ports (and optional GraphDB window).

.DESCRIPTION
  From repo root:
    .\scripts\dev\stop-stack.ps1
    .\scripts\dev\stop-stack.ps1 -IncludeGraphDb
#>
[CmdletBinding()]
param(
    [int[]]$Ports = @(8000, 8001, 5173),
    [switch]$IncludeGraphDb
)

$ErrorActionPreference = "Continue"

function Stop-PortListeners([int]$Port) {
    $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $conns) {
        Write-Output "  :$Port idle"
        return
    }
    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        try {
            $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
            $name = if ($p) { $p.ProcessName } else { "?" }
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Output "  stopped pid=$procId ($name) on :$Port"
        }
        catch {
            Write-Output "  could not stop pid=$procId on :$Port"
        }
    }
}

Write-Output "=== LoanOps stop-stack ==="
foreach ($port in $Ports) {
    Stop-PortListeners -Port $port
}

if ($IncludeGraphDb) {
    Write-Output "Stopping GraphDB Java listeners on :7200 (if any)"
    Stop-PortListeners -Port 7200
    Get-Process -Name "graphdb*" -ErrorAction SilentlyContinue |
        ForEach-Object {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            Write-Output "  stopped $($_.ProcessName) pid=$($_.Id)"
        }
}

Write-Output "Done. Postgres left running (shared). Status:"
uv run python (Join-Path $PSScriptRoot "stack_ops.py") status
