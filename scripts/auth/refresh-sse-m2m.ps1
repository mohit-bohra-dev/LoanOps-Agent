#Requires -Version 5.1
<#
.SYNOPSIS
  Mint SubservicingClient Auth0 M2M token and write SSE__API_KEY in LoanOps .env (D7).

.DESCRIPTION
  Uses client_credentials against Auth0M2M (audience https://pennymac).
  Client secret from SubservicingClient user-secrets by default (never commit secrets).

  Usage (from LoanOps repo root):
    .\scripts\auth\refresh-sse-m2m.ps1
    .\scripts\auth\refresh-sse-m2m.ps1 -ProbeUrl "https://loanservicesapi-plaisse-dev.pnmac.com/api/Loans/1000002245/Summary"
#>
[CmdletBinding()]
param(
    [string]$LoanOpsRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$SubservicingWebProject = "D:\Users\v-mbohra\Documents\Projects\subservicingclient\src\SubservicingClient.Web",
    [string]$Domain = "auth.dev.pennymac.plaisse.com",
    [string]$ClientId = "yY1wP158rVkx6z9lxdneav8JFWNGpTZ2",
    [string]$Audience = "https://pennymac",
    [string]$ProbeUrl = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $SubservicingWebProject)) {
    throw "Subservicing web project not found: $SubservicingWebProject"
}

Push-Location $SubservicingWebProject
try {
    $secrets = @{}
    dotnet user-secrets list | ForEach-Object {
        if ($_ -match '^\s*(.+?)\s*=\s*(.*)$') {
            $secrets[$Matches[1].Trim()] = $Matches[2].Trim()
        }
    }
}
finally {
    Pop-Location
}

$clientSecret = $secrets["Auth0M2M:ClientSecret"]
if ([string]::IsNullOrWhiteSpace($clientSecret)) {
    throw "Auth0M2M:ClientSecret missing. Set it: dotnet user-secrets set `"Auth0M2M:ClientSecret`" `"...`" --project `"$SubservicingWebProject`""
}

$body = @{
    grant_type    = "client_credentials"
    client_id     = $ClientId
    client_secret = $clientSecret
    audience      = $Audience
}
$tokenUrl = "https://$Domain/oauth/token"
$resp = Invoke-RestMethod -Method Post -Uri $tokenUrl -ContentType "application/x-www-form-urlencoded" -Body $body
$token = $resp.access_token
$expires = $resp.expires_in
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Auth0 returned empty access_token"
}

$envPath = Join-Path $LoanOpsRoot ".env"
if (-not (Test-Path $envPath)) {
    throw ".env not found at $envPath"
}

$lines = Get-Content $envPath
$found = $false
$out = foreach ($line in $lines) {
    if ($line -match '^\s*SSE__API_KEY\s*=') {
        $found = $true
        "SSE__API_KEY=$token"
    }
    else {
        $line
    }
}
if (-not $found) {
    $out += "SSE__API_KEY=$token"
}
Set-Content -Path $envPath -Value $out -Encoding utf8

$status = "skipped"
if (-not [string]::IsNullOrWhiteSpace($ProbeUrl)) {
    $headers = @{ Authorization = "Bearer $token" }
    try {
        $r = Invoke-WebRequest -Uri $ProbeUrl -Headers $headers -Method GET -UseBasicParsing
        $status = [int]$r.StatusCode
    }
    catch {
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        else {
            $status = "ERR"
        }
    }
}

Write-Output "SSE__API_KEY updated (token_len=$($token.Length) expires_in=$expires probe=$status)"
# Never print the token.
