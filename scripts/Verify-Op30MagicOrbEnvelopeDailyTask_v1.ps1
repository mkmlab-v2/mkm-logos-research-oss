#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM_Op30_MagicOrb_Envelope_Daily scheduled task and latest Op30 report.
#>
param(
    [string]$TaskName = "MKM_Op30_MagicOrb_Envelope_Daily",
    [string]$ReportPath = "C:\workspace\reports\op30_phase2_daily_latest.json"
)

$ErrorActionPreference = "Stop"
$failed = @()

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "[verify-op30] MISSING task: $TaskName"
    $failed += "task_missing"
} else {
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host "[verify-op30] task=$TaskName state=$($task.State) lastResult=$($info.LastTaskResult) nextRun=$($info.NextRunTime)"
    if ($task.State -ne "Ready") { $failed += "task_not_ready" }
}

if (Test-Path -LiteralPath $ReportPath) {
    $report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host "[verify-op30] report schema=$($report.schema) failed_steps=$($report.failed_steps.Count) kv_ok=$($report.internal_kv_sync_ok)"
    if ($report.failed_steps -and $report.failed_steps.Count -gt 0) {
        $failed += "report_failed_steps"
    }
} else {
    Write-Host "[verify-op30] report missing: $ReportPath"
    $failed += "report_missing"
}

if ($failed.Count -gt 0) {
    Write-Host "[verify-op30] FAIL: $($failed -join ', ')" -ForegroundColor Yellow
    exit 1
}

Write-Host "[verify-op30] OK" -ForegroundColor Green
exit 0
