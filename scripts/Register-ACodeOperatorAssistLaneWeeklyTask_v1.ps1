#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Task Scheduler job for A-code operator-assist lane (RQ-031 · [HYPO]).

.DESCRIPTION
  Wraps scripts/Run-ACodeOperatorAssistLaneRoutine_v1.ps1 (full governor + promotion rq + lane freeze).
  Default: Sunday 09:05 local · **full** profile (multiday governor 포함).
  경량 프로파일: `-SkipGovernorBundle` — promotion rq + lane freeze만(주간 multiday 생략).
  별도 Task 등록 시 `-TaskName MKM-ACode-OperatorAssistLane-Weekly-Light` 권장.

.EXAMPLE
  pwsh -File scripts/Register-ACodeOperatorAssistLaneWeeklyTask_v1.ps1 -DryRun
  pwsh -File scripts/Register-ACodeOperatorAssistLaneWeeklyTask_v1.ps1 -SkipGovernorBundle -TaskName MKM-ACode-OperatorAssistLane-Weekly-Light
  pwsh -File scripts/Register-ACodeOperatorAssistLaneWeeklyTask_v1.ps1 -Remove
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-ACode-OperatorAssistLane-Weekly",
    [ValidateSet("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")]
    [string]$DayOfWeek = "Sunday",
    [string]$RunAt = "09:05",
    [switch]$SkipGovernorBundle,
    [switch]$Strict,
    [switch]$DryRun,
    [switch]$Remove,
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[REMOVED] $TaskName" -ForegroundColor Yellow
    exit 0
}

$routine = Join-Path $WorkspaceRoot "scripts\Run-ACodeOperatorAssistLaneRoutine_v1.ps1"
if (-not (Test-Path -LiteralPath $routine)) {
    throw "Required script not found: $routine"
}

try {
    [void][DateTime]::ParseExact($RunAt, "HH:mm", $null)
} catch {
    throw "RunAt must be HH:mm format, e.g. 09:05"
}

$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$routine`" -WorkspaceRoot `"$WorkspaceRoot`""
if ($SkipGovernorBundle) { $argument += " -SkipGovernorBundle" }
if ($Strict) { $argument += " -Strict" }

if ($DryRun) {
    Write-Host "scheduled_task: DRY_RUN" -ForegroundColor DarkGray
    Write-Host "would_register_task_name=$TaskName"
    Write-Host "would_run_weekly_day=$DayOfWeek run_at=$RunAt"
    Write-Host "working_directory=$WorkspaceRoot"
    Write-Host "powershell_argument=$argument"
    exit 0
}

$actionParams = @{
    Execute  = "powershell.exe"
    Argument = $argument
}
try {
    $action = New-ScheduledTaskAction @actionParams -WorkingDirectory $WorkspaceRoot
} catch {
    $action = New-ScheduledTaskAction @actionParams
}

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $RunAt
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null

$meta = [ordered]@{
    schema             = "a_code_operator_assist_lane_weekly_task_v1"
    generated_at_utc   = (Get-Date).ToUniversalTime().ToString("o")
    task_name          = $TaskName
    weekly_day         = $DayOfWeek
    run_at             = $RunAt
    routine_script     = "scripts/Run-ACodeOperatorAssistLaneRoutine_v1.ps1"
    skip_governor_bundle = [bool]$SkipGovernorBundle
    profile              = if ($SkipGovernorBundle) { "weekly_light_skip_governor" } else { "weekly_full_multiday" }
    strict             = [bool]$Strict
    rq_id              = "RQ-031"
    hypothesis_tier    = "B"
    research_only      = $true
    non_gating         = $true
    track_wall         = "no_track_a_live_auto_merge"
    verify_command     = "pwsh -File scripts/Verify-ACodeOperatorAssistLaneReadiness_v1.ps1"
}
$outJson = Join-Path $WorkspaceRoot "reports\a_code_operator_assist_lane_weekly_task_latest.json"
$meta | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outJson -Encoding utf8

Write-Host "[REGISTERED] $TaskName ($DayOfWeek $RunAt)" -ForegroundColor Green
Write-Host "Wrote $outJson" -ForegroundColor DarkGray

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "[STARTED] $TaskName" -ForegroundColor Green
}

exit 0
