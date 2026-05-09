<#
.SYNOPSIS
  Register weekly scheduled task for Myeongni+Sasang fusion wrapper.

.DESCRIPTION
  Wraps scripts/Run-MyeongniSasangWeeklyFusion_v1.ps1.
  Default: every Sunday at 07:40 (local machine time).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-MyeongniSasangWeeklyFusionTask.ps1 -DryRun
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-MyeongniSasangWeeklyFusionTask.ps1 -Include16StateProbe
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-MyeongniSasang-WeeklyFusion",
    [ValidateSet("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")]
    [string]$DayOfWeek = "Sunday",
    [string]$RunAt = "07:40",
    [switch]$Include16StateProbe,
    [switch]$SkipYFinance,
    [switch]$SkipBioRehydrate,
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

$fusionScript = Join-Path $PSScriptRoot "Run-MyeongniSasangWeeklyFusion_v1.ps1"
if (-not (Test-Path -LiteralPath $fusionScript)) {
    throw "Required script not found: $fusionScript"
}

try {
    [void][DateTime]::ParseExact($RunAt, "HH:mm", $null)
}
catch {
    throw "RunAt must be HH:mm format, e.g. 07:40"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$fusionScript`""
if ($Include16StateProbe) { $argument += " -Include16StateProbe" }
if ($SkipYFinance) { $argument += " -SkipYFinance" }
if ($SkipBioRehydrate) { $argument += " -SkipBioRehydrate" }

if ($DryRun) {
    Write-Output "scheduled_task: DRY_RUN (no Register/Unregister performed)"
    Write-Output "would_register_task_name=$TaskName"
    Write-Output "would_run_weekly_day=$DayOfWeek"
    Write-Output "would_run_at=$RunAt"
    Write-Output ("include16stateprobe={0} skip_yfinance={1} skip_bio_rehydrate={2}" -f @(
            [bool]$Include16StateProbe, [bool]$SkipYFinance, [bool]$SkipBioRehydrate))
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
Write-Output ("include16stateprobe={0} skip_yfinance={1} skip_bio_rehydrate={2}" -f @(
        [bool]$Include16StateProbe, [bool]$SkipYFinance, [bool]$SkipBioRehydrate))
Write-Output "script=$fusionScript"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
