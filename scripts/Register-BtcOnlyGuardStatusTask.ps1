<#
.SYNOPSIS
  Register (or remove) a scheduled task for BTC-only guard status checks.

.DESCRIPTION
  Runs: py scripts/check_btc_only_guard_status_v1.py --strict-exit
  Default: every 4 hours, thin probe only.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_BTC_Only_Guard_Status",
    [int]$IntervalHours = 4,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\check_btc_only_guard_status_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task (if existed): $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if ($IntervalHours -lt 1 -or $IntervalHours -gt 24) {
    throw "IntervalHours must be between 1 and 24, got: $IntervalHours"
}

$start = (Get-Date).AddMinutes(2)
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"Set-Location -LiteralPath '$WorkspaceRoot'; py '$runner' --strict-exit`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Once -At $start `
    -RepetitionInterval (New-TimeSpan -Hours $IntervalHours) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Every ${IntervalHours}h: BTC-only guard status check (blocked/mismatch)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (every $IntervalHours hours from $start)"
Write-Host "Runner: $runner"
