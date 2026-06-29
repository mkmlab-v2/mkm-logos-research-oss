#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly B-track fills archive backfill (primary SSOT hygiene).

.PARAMETER Remove
  Unregister scheduled task.

.PARAMETER SundayAt
  Local HH:mm (default 06:45).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-BtrackFillsWeeklyBackfillTask.ps1
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Btrack_Fills_WeeklyBackfill",
    [string]$SundayAt = "06:45"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-BtrackFillsArchiveBackfill_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$workspaceRoot`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Registered: $TaskName (Sunday $SundayAt) -> $runner"
