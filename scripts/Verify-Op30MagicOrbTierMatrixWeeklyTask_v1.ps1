#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM_Op30_MagicOrb_TierMatrix_Weekly task and latest weekly tier-matrix report.
#>
param(
    [string]$TaskName = "MKM_Op30_MagicOrb_TierMatrix_Weekly",
    [string]$ReportPath = "C:\workspace\reports\op30_magic_orb_tier_matrix_weekly_latest.json"
)

$ErrorActionPreference = "Stop"
$failed = @()

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "[verify-tier-weekly] MISSING task: $TaskName"
    $failed += "task_missing"
} else {
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host "[verify-tier-weekly] task=$TaskName state=$($task.State) lastResult=$($info.LastTaskResult) nextRun=$($info.NextRunTime)"
    if ($task.State -ne "Ready") { $failed += "task_not_ready" }
}

if (Test-Path -LiteralPath $ReportPath) {
    $report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host "[verify-tier-weekly] report schema=$($report.schema) tier_ok=$($report.tier_matrix_smoke_ok) preview_ok=$($report.oracle_preview_smoke_ok)"
    if ($report.tier_matrix_smoke_ok -ne $true) { $failed += "tier_matrix_not_ok" }
} else {
    Write-Host "[verify-tier-weekly] report missing: $ReportPath (run Invoke-Op30MagicOrbWeeklyTierMatrix_v1.ps1 once)"
    $failed += "report_missing"
}

if ($failed.Count -gt 0) {
    Write-Host "[verify-tier-weekly] FAIL: $($failed -join ', ')" -ForegroundColor Yellow
    exit 1
}

Write-Host "[verify-tier-weekly] OK" -ForegroundColor Green
exit 0
