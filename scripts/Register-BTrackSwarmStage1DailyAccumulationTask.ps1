<#
.SYNOPSIS
  Register weekday daily task for Stage 1 tier_a ATProto accumulation (B-track only).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_BTrack_SwarmStage1_DailyAccumulation

.PARAMETER DailyAt
  Local time HH:mm on Mon–Fri (default: 08:30).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_BTrack_SwarmStage1_DailyAccumulation",
    [string]$DailyAt = "08:30"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-BTrackSwarmStage1DailyAccumulation_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 08:30), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "B-track Stage1: Bluesky collect + backfill + tier_a ingest; re-eval at 30 rows only."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (Mon-Fri $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
