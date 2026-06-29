<#
.SYNOPSIS
  Register weekly Scheduled Task: Science Core governance bundle (B-track research_only).

.DESCRIPTION
  Runs: Run-ScienceCoreGovernanceBundle_v1.ps1 -ExtendCalendarStubs -RebuildScience
  Default: Sunday 09:00 local (after Logos chronology 08:30 if both registered).

.PARAMETER Remove
  Unregister the task.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_ScienceCore_WeeklyGovernance",
    [string]$SundayAt = "09:00"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-ScienceCoreGovernanceBundle_v1.ps1"

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

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$runner"" -ExtendCalendarStubs -RebuildScience -ExportSidecarHumanist -RunHumanistAb -RunLogosAb -UseFullHumanistPerDate -RunLongWalkforward -RunNewsWeightAblation -RunLongWindowLaneCompare -RunTripleBlendWeightSweep -RunPnlBootstrap"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Enable-ScheduledTask -TaskName $TaskName | Out-Null
Write-Host "Registered (Enabled): $TaskName (Sunday $SundayAt) -> Run-ScienceCoreGovernanceBundle_v1.ps1"
