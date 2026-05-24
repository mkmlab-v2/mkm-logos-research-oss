<#
.SYNOPSIS
  Register weekly Task Scheduler job for patient intake fusion B-track chain.

.DESCRIPTION
  Wraps scripts/Run-PatientIntakeFusionBtrackWeeklyOps_v1.ps1 (chain + deploy + VPS sync + public smoke).
  Default: Sunday 08:15 (local). ijeoma harvest/prune off by default (pass -ApplyIjeomaHarvest when registering).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-PatientIntakeFusionWeeklyTask_v1.ps1 -DryRun
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-PatientIntakeFusionWeeklyTask_v1.ps1 -StartNow
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-PatientIntakeFusion-Weekly",
    [ValidateSet("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")]
    [string]$DayOfWeek = "Sunday",
    [string]$RunAt = "08:15",
    [switch]$SkipSyncToVps,
    [switch]$SkipPublicSmoke,
    [switch]$BuildAllConstitutions,
    [switch]$ApplyIjeomaHarvest,
    [switch]$PruneIjeomaHarvestLexicon,
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

$opsScript = Join-Path $PSScriptRoot "Run-PatientIntakeFusionBtrackWeeklyOps_v1.ps1"
if (-not (Test-Path -LiteralPath $opsScript)) {
    throw "Required script not found: $opsScript"
}

try {
    [void][DateTime]::ParseExact($RunAt, "HH:mm", $null)
}
catch {
    throw "RunAt must be HH:mm format, e.g. 08:15"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$opsScript`""
if ($SkipSyncToVps) { $argument += " -SkipSyncToVps" }
if ($SkipPublicSmoke) { $argument += " -SkipPublicSmoke" }
if ($BuildAllConstitutions) { $argument += " -BuildAllConstitutions" }
if ($ApplyIjeomaHarvest) { $argument += " -ApplyIjeomaHarvest" }
if ($PruneIjeomaHarvestLexicon) { $argument += " -PruneIjeomaHarvestLexicon" }

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
