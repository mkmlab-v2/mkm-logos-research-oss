<# 
.SYNOPSIS
  Register (or remove) scheduled task for core task consecutive failure alert.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_CoreTask_ConsecutiveFailure_Alert_15min",
    [int]$IntervalMinutes = 15
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\build_core_task_consecutive_failure_alert_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$startAt = (Get-Date).AddMinutes(1)

$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"py '$runner'`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $workspaceRoot
$repeatDuration = New-TimeSpan -Days 3650
$trigger = New-ScheduledTaskTrigger -Once -At $startAt `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration $repeatDuration
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Build core task consecutive-failure alert artifact every $IntervalMinutes minutes."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (every $IntervalMinutes minutes)"
Write-Host "Runner: $runner"
