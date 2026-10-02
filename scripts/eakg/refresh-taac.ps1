#Requires -Version 5.1
<#
.SYNOPSIS
  Refresh live TAAC client config into .eakg-workspace via glab (never commits).

.NOTES
  Override project path with -ProjectPath. Output is gitignored.
  Point EAKG__TAAC_CONFIG_PATH at the written file before ingest / nightly.
#>
param(
    [string]$ProjectPath = "servicing/plaisse/applications/taac",
    [string]$HostName = "gitlab.pnmac.com",
    [string]$OutFile = ""
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root
$ws = Join-Path $Root ".eakg-workspace"
New-Item -ItemType Directory -Force -Path $ws | Out-Null
if (-not $OutFile) {
    $OutFile = Join-Path $ws "taac-client-config.json"
}
# Common TAAC artifact paths — try file API; fail soft with message if missing.
$candidates = @(
    "src/TAAC.Client/appsettings.json",
    "TAAC.Client/appsettings.json",
    "client-config.json"
)
$encoded = [uri]::EscapeDataString($ProjectPath)
$got = $false
foreach ($rel in $candidates) {
    $fileEnc = [uri]::EscapeDataString($rel)
    $api = "projects/$encoded/repository/files/$fileEnc/raw?ref=main"
    $tmp = Join-Path $env:TEMP "eakg-taac-raw.json"
    & glab api --hostname $HostName $api > $tmp 2>$null
    if ($? -and (Test-Path $tmp) -and ((Get-Item $tmp).Length -gt 20)) {
        Move-Item -Force $tmp $OutFile
        Write-Output "Wrote $OutFile from $ProjectPath/$rel"
        $got = $true
        break
    }
}
if (-not $got) {
    Write-Error "TAAC refresh failed. Set -ProjectPath to the GitLab project that holds client config, or copy manually to $OutFile"
    exit 1
}
Write-Output "Next: `$env:EAKG__TAAC_CONFIG_PATH='$OutFile'; uv run python -m packages.eakg ingest-taac --path `"$OutFile`""
