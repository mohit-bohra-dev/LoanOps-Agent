#Requires -Version 5.1
<#
.SYNOPSIS
  Register Windows Task Scheduler jobs for EAKG nightly + weekly audit.
#>
param(
    [string]$NightlyTime = "02:00",
    [string]$AuditTime = "06:00"
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$nightly = Join-Path $PSScriptRoot "sync-nightly.ps1"
$audit = Join-Path $PSScriptRoot "sync-audit.ps1"

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable

Unregister-ScheduledTask -TaskName "LoanOps-EAKG-Nightly" -Confirm:$false -ErrorAction SilentlyContinue
$actionN = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$nightly`"" `
    -WorkingDirectory $Root
$trigN = New-ScheduledTaskTrigger -Daily -At $NightlyTime
Register-ScheduledTask -TaskName "LoanOps-EAKG-Nightly" -Action $actionN -Trigger $trigN -Settings $settings | Out-Null
Write-Output "Registered LoanOps-EAKG-Nightly"

Unregister-ScheduledTask -TaskName "LoanOps-EAKG-Audit" -Confirm:$false -ErrorAction SilentlyContinue
$actionA = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$audit`"" `
    -WorkingDirectory $Root
$trigA = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $AuditTime
Register-ScheduledTask -TaskName "LoanOps-EAKG-Audit" -Action $actionA -Trigger $trigA -Settings $settings | Out-Null
Write-Output "Registered LoanOps-EAKG-Audit"
Write-Output "Done. See docs/EAKG_INDEX_SCHEDULE.md"
