<#
.SYNOPSIS
  Run monthly emotion-state promotion drill and append log.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$Reviewer = "PRO"
)

$ErrorActionPreference = "Stop"

$drillRunner = Join-Path $WorkspaceRoot "scripts\run_emotion_state_monthly_promotion_drill_v1.py"
$appendRunner = Join-Path $WorkspaceRoot "scripts\append_emotion_state_monthly_drill_log_v1.py"
$drillSummary = Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_monthly_promotion_drill_summary_latest.json"
$logSummary = Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_monthly_drill_log_summary_latest.json"
$logJsonl = Join-Path $WorkspaceRoot "reports\emotion_state_monthly_drill_log.jsonl"

if (-not (Test-Path -LiteralPath $drillRunner)) {
    throw "Drill runner not found: $drillRunner"
}
if (-not (Test-Path -LiteralPath $appendRunner)) {
    throw "Log append runner not found: $appendRunner"
}

& py $drillRunner `
    --promotion-gate (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_promotion_gate_latest.json") `
    --mapping-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_mapping_latest.json") `
    --reviewer $Reviewer `
    --summary-json $drillSummary
if ($LASTEXITCODE -ne 0) { throw "Emotion monthly drill failed ($LASTEXITCODE)" }

& py $appendRunner `
    --drill-result-json $drillSummary `
    --log-jsonl $logJsonl `
    --summary-json $logSummary
if ($LASTEXITCODE -ne 0) { throw "Emotion monthly drill log append failed ($LASTEXITCODE)" }

Write-Host "DONE: emotion-state monthly promotion drill chain"
Write-Host "Drill summary: $drillSummary"
Write-Host "Log summary: $logSummary"
