#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM Prophecy Sandbox scheduled tasks (daily + weekly Phase3).

.OUTPUTS
  JSON-friendly lines: task_name, state, arguments, checks.*
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$DailyTaskName = "MKM-Prophecy-Sandbox-DailyChain",
    [string]$WeeklyTaskName = "MKM-Prophecy-Sandbox-WeeklyPhase3",
    [string]$OutJson = "",
    [switch]$RequireWeeklyLastSuccess
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-TaskSnapshot {
    param([string]$Name)
    $t = Get-ScheduledTask -TaskName $Name -ErrorAction Stop
    $info = Get-ScheduledTaskInfo -InputObject $t
    $a = $t.Actions[0]
  return [ordered]@{
        task_name           = $Name
        state               = [string]$t.State
        last_run_time       = $info.LastRunTime.ToString("o")
        last_task_result    = $info.LastTaskResult
        execute             = [string]$a.Execute
        arguments           = [string]$a.Arguments
        working_directory   = [string]$a.WorkingDirectory
    }
}

$daily = Get-TaskSnapshot -Name $DailyTaskName
$weekly = Get-TaskSnapshot -Name $WeeklyTaskName

# SCHED_S_TASK_HAS_NOT_RUN (0x41301) / never-scheduled sentinel — not a registration defect.
$neverRunCodes = @(0, 267009, 267011)
$weeklyNeverRun = ($weekly.last_task_result -in $neverRunCodes) -or ($weekly.last_run_time -like "1999-*")
$weeklyRunOk = ($weekly.last_task_result -eq 0) -or ((-not $RequireWeeklyLastSuccess) -and $weeklyNeverRun)

$checks = [ordered]@{
    daily_has_refresh_phase3_join      = ($daily.arguments -match "--refresh-phase3-join")
    daily_has_backfill_stream_calendar = ($daily.arguments -match "--backfill-stream-calendar")
    daily_has_sync_daily_thread_log    = ($daily.arguments -match "--sync-daily-thread-log")
    weekly_uses_weekly_entry           = ($weekly.arguments -match "run_prophecy_sandbox_weekly_phase3_v1.py")
    weekly_has_binance                 = ($weekly.arguments -match "run_prophecy_sandbox_weekly_phase3_v1.py|refresh-phase3-binance")
    weekly_has_join                    = ($weekly.arguments -match "run_prophecy_sandbox_weekly_phase3_v1.py|refresh-phase3-join")
    daily_ready                        = ($daily.state -eq "Ready")
    weekly_ready                       = ($weekly.state -eq "Ready")
    weekly_last_run_acceptable         = $weeklyRunOk
}

$ok = $checks.daily_has_refresh_phase3_join -and $checks.daily_has_backfill_stream_calendar `
    -and $checks.daily_has_sync_daily_thread_log `
    -and $checks.weekly_uses_weekly_entry -and $checks.weekly_has_binance -and $checks.weekly_has_join `
    -and $checks.daily_ready -and $checks.weekly_ready -and $checks.weekly_last_run_acceptable

Write-Output "schema=prophecy_sandbox_scheduled_tasks_verify_v1"
Write-Output ("ok=$ok")
foreach ($k in $checks.Keys) {
    Write-Output ("check.$k=$($checks[$k])")
}
foreach ($k in $daily.Keys) {
    Write-Output ("daily.$k=$($daily[$k])")
}
foreach ($k in $weekly.Keys) {
    Write-Output ("weekly.$k=$($weekly[$k])")
}

if ($OutJson) {
    $outPath = if ([System.IO.Path]::IsPathRooted($OutJson)) { $OutJson } else { Join-Path $WorkspaceRoot $OutJson }
    $report = [ordered]@{
        schema       = "prophecy_sandbox_scheduled_tasks_verify_v1"
        generated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        ok           = [bool]$ok
        checks       = $checks
        daily        = $daily
        weekly       = $weekly
    }
    $dir = Split-Path -Parent $outPath
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    ($report | ConvertTo-Json -Depth 6) + "`n" | Set-Content -LiteralPath $outPath -Encoding utf8
    Write-Output "WROTE: $outPath"
}

if (-not $ok) { exit 1 }
exit 0
