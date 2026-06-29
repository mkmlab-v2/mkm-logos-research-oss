<#
.SYNOPSIS
  Register weekly Task Scheduler job for TKM encounter_sequence report chain.

.DESCRIPTION
  Wraps scripts/Invoke-TkmEncounterSequenceWeeklyOps_v1.ps1 (P26 ops closure chain).
  Default: Sunday 09:30 local (after Sasang rail stack 09:00).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-TkmEncounterSequenceWeeklyReport_v1.ps1 -DryRun
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-TkmEncounterSequenceWeeklyReport_v1.ps1 -StartNow
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-TkmEncounterSequence-Weekly",
    [ValidateSet("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")]
    [string]$DayOfWeek = "Sunday",
    [string]$RunAt = "09:30",
    [switch]$SkipPytest,
    [switch]$DryRun,
    [switch]$Remove,
    [switch]$StartNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$opsScript = Join-Path $PSScriptRoot "Invoke-TkmEncounterSequenceWeeklyOps_v1.ps1"
if (-not (Test-Path -LiteralPath $opsScript)) {
    throw "Required script not found: $opsScript"
}

try {
    [void][DateTime]::ParseExact($RunAt, "HH:mm", $null)
}
catch {
    throw "RunAt must be HH:mm format, e.g. 09:30"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$opsScript`""
if ($SkipPytest) { $argument += " -SkipPytest" }

if ($DryRun) {
    Write-Output "scheduled_task: DRY_RUN (no Register/Unregister performed)"
    Write-Output "would_register_task_name=$TaskName"
    Write-Output "would_run_weekly_day=$DayOfWeek"
    Write-Output "would_run_at=$RunAt"
    Write-Output "working_directory=$repoRoot"
    Write-Output "powershell_argument=$argument"
    if ($StartNow) { Write-Output "would_start_now=true (ignored under DryRun)" }
    exit 0
}

$actionParams = @{
    Execute = "powershell.exe"
    Argument = $argument
}
try {
    $action = New-ScheduledTaskAction @actionParams -WorkingDirectory $repoRoot
}
catch {
    $action = New-ScheduledTaskAction @actionParams
}

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $RunAt
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "weekly_day=$DayOfWeek run_at=$RunAt"
Write-Output "script=$opsScript"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
