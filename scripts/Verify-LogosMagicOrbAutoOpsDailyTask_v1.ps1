#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM_Logos_MagicOrb_AutoOps_Daily scheduled task and latest auto ops report.
#>
param(
    [string]$TaskName = "MKM_Logos_MagicOrb_AutoOps_Daily",
    [string]$ReportPath = "C:\workspace\reports\logos_magic_orb_auto_ops_v1_latest.json"
)

$ErrorActionPreference = "Stop"
$failed = @()

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "[verify-logos-auto-ops] MISSING task: $TaskName"
    $failed += "task_missing"
} else {
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    $action = ($task.Actions | Select-Object -First 1).Arguments
    Write-Host "[verify-logos-auto-ops] task=$TaskName state=$($task.State) lastResult=$($info.LastTaskResult) nextRun=$($info.NextRunTime)"
    Write-Host "[verify-logos-auto-ops] action_args=$action"
    if ($task.State -ne "Ready") { $failed += "task_not_ready" }
    if ($action -notmatch "Run-LogosMagicOrbAutoOps_v1\.ps1") { $failed += "wrong_runner" }
    if ($action -notmatch "-SkipRebuild") { $failed += "skip_rebuild_missing" }
}

if (Test-Path -LiteralPath $ReportPath) {
    $report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host "[verify-logos-auto-ops] report auto_ok=$($report.auto_ok) deploy_auth_mode=$($report.deploy_auth_mode) deploy_token_ready=$($report.deploy_token_ready)"
    if (-not $report.auto_ok) { $failed += "report_auto_ok_false" }
} else {
    Write-Host "[verify-logos-auto-ops] report missing: $ReportPath"
    $failed += "report_missing"
}

if ($failed.Count -gt 0) {
    Write-Host "[verify-logos-auto-ops] FAIL: $($failed -join ', ')" -ForegroundColor Yellow
    exit 1
}

Write-Host "[verify-logos-auto-ops] OK" -ForegroundColor Green
exit 0
