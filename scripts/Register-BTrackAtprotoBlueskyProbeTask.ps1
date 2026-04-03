<#
.SYNOPSIS
  Register a weekly Scheduled Task for B-track Bluesky probe (optional; not in automation_registry).

.DESCRIPTION
  Does not touch automation_registry.json or verify_all_green. Register only if you want hands-off runs.
  Credentials must be in the interactive user's environment (BSKY_HANDLE, BSKY_APP_PASSWORD).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_BTrack_AtprotoBluesky_Weekly

.PARAMETER WeeklyAt
  Local time HH:mm for weekly Sunday trigger (default: 09:00).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_BTrack_AtprotoBluesky_Weekly",
    [string]$WeeklyAt = "09:00"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-BTrackAtprotoBlueskyProbe.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WeeklyAt -split ':'
if ($parts.Count -lt 2) {
    throw "WeeklyAt must be HH:mm (e.g. 09:00), got: $WeeklyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "B-track experiment: Bluesky ATProto sample JSONL (no live trading). Skips if BSKY_* unset."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $WeeklyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "One-time: py -m pip install atproto"
Write-Host "Set User env: BSKY_HANDLE, BSKY_APP_PASSWORD (see .env.example)"
