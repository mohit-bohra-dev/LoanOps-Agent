#Requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryId
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root
$uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
if (-not (Test-Path $uv)) { $uv = "uv" }
& $uv run python -m packages.eakg sync repo --id $RepositoryId
if (-not $?) { exit 1 }
