param(
    [ValidateSet("mock","real")]
    [string]$Mode = "mock"
)
Copy-Item ".env.$Mode" ".env" -Force
Write-Host "Switched to $Mode mode. Restart services to apply."
