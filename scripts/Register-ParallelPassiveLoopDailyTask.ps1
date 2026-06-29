#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily hidden Task Scheduler job for 3-lane parallel passive loop (no Nebius).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-ParallelPassiveLoopDailyTask.ps1 -At "09:15"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-ParallelPassiveLoopDailyTask.ps1 -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_ParallelPassiveLoop_Daily",
    [string]$At = "09:15",
    [switch]$RunWhenLoggedOff,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-ParallelPassiveLoop_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ($RunWhenLoggedOff) {
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "[OK] Registered: $TaskName daily at $At" -ForegroundColor Green
Write-Host "  Runner: $runner (3 lanes; D Nebius STOP by default)" -ForegroundColor DarkGray
