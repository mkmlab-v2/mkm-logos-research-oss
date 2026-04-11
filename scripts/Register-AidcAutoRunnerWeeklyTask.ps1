<#
.SYNOPSIS
  Register (or remove) a weekly Scheduled Task for bounded AIDC v2 auto runner.

.DESCRIPTION
  Runs scripts/run_aidc_auto_runner.ps1 -MaxCycles 1 (single cycle, then exit).
  B-Track observation lane only; does not stop other OPS automation.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_AIDC_AutoRunner_Weekly).

.PARAMETER SaturdayAt
  Local time HH:mm for weekly Saturday trigger (default: 09:00).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_AIDC_AutoRunner_Weekly",
    [string]$SaturdayAt = "09:00"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_aidc_auto_runner.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SaturdayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SaturdayAt must be HH:mm (e.g. 09:00), got: $SaturdayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -MaxCycles 1 -AidcOutputSuffix _v2"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Saturday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly bounded AIDC v2 run (Fact-Lock chain + gate). MaxCycles=1; B-Track observation only."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Saturday $SaturdayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
