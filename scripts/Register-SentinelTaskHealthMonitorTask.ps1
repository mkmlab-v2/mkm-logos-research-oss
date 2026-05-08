<#
.SYNOPSIS
  Register/remove periodic sentinel task-health monitor.
#>
param(
  [switch]$Remove,
  [string]$TaskName = "MKM_Sentinel_TaskHealth_Monitor_15m",
  [int]$EveryMinutes = 15
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\emit_sentinel_from_task_health_v1.py"

if ($Remove) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task: $TaskName"
  exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner not found: $runner"
}
if ($EveryMinutes -lt 5) {
  throw "EveryMinutes must be >= 5"
}

$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"py '$runner'`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
$repeatDuration = New-TimeSpan -Days 3650
$trigger.Repetition = (
  New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) `
    -RepetitionDuration $repeatDuration
).Repetition

$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Settings $settings -Principal $principal -Description "Sentinel realtime emission from task health monitor." -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (every $EveryMinutes min)"
Write-Host "Runner: $runner"

