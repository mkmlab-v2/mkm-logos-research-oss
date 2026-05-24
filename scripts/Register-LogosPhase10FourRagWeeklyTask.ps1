<#
.SYNOPSIS
  Register weekly Scheduled Task: LOGOS Phase10 4RAG envelope refresh (local + optional VPS).

.DESCRIPTION
  Runs Run-LogosPhase10FourRagEnvelopeRefresh_v1.ps1 with -SkipOlAtoms (weekly refresh; OL on demand).
  Default: Sunday 09:00 local (after compression governance 07:00 / chronology 08:30).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_Logos_Phase10_FourRag_Weekly).

.PARAMETER SundayAt
  Local time HH:mm for weekly Sunday trigger (default: 09:00).

.PARAMETER SkipVpsSync
  Pass -SkipVpsSync to Phase10 runner (staging/local only).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Logos_Phase10_FourRag_Weekly",
    [string]$SundayAt = "09:00",
    [switch]$SkipVpsSync
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-LogosPhase10FourRagEnvelopeRefresh_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SundayAt must be HH:mm (e.g. 09:00), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$skipVps = if ($SkipVpsSync) { " -SkipVpsSync" } else { "" }
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -SkipOlAtoms$skipVps"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "Registered: $TaskName (Sunday $SundayAt)"
Write-Host "Runner: $runner -SkipOlAtoms$skipVps"
