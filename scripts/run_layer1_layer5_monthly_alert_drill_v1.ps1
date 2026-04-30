<#
.SYNOPSIS
  Run monthly Layer1/Layer5 readiness alert drill.

.DESCRIPTION
  Executes drill generator and optionally performs one live webhook dispatch test.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$LiveDispatch
)

$ErrorActionPreference = "Stop"

$drillRunner = Join-Path $WorkspaceRoot "scripts\run_layer1_layer5_readiness_alert_drill_v1.py"
$alertRunner = Join-Path $WorkspaceRoot "scripts\send_layer1_layer5_readiness_alert_v1.py"
$drillReadiness = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_governance_readiness_drill_latest.json"
$drillAlert = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_readiness_alert_drill_latest.json"
$drillSummary = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_readiness_alert_drill_summary_latest.json"
$liveAlertOut = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_readiness_alert_live_test_latest.json"

if (-not (Test-Path -LiteralPath $drillRunner)) {
    throw "Drill runner not found: $drillRunner"
}
if (-not (Test-Path -LiteralPath $alertRunner)) {
    throw "Alert runner not found: $alertRunner"
}

& py $drillRunner `
    --readiness-json $drillReadiness `
    --alert-result-json $drillAlert `
    --summary-json $drillSummary
if ($LASTEXITCODE -ne 0) { throw "Drill runner failed ($LASTEXITCODE)" }

if ($LiveDispatch) {
    & py $alertRunner `
        --readiness-json $drillReadiness `
        --output-json $liveAlertOut
    if ($LASTEXITCODE -ne 0) { throw "Live alert dispatch failed ($LASTEXITCODE)" }
} else {
    & py $alertRunner `
        --readiness-json $drillReadiness `
        --output-json $liveAlertOut `
        --dry-run
    if ($LASTEXITCODE -ne 0) { throw "Dry-run alert dispatch failed ($LASTEXITCODE)" }
}

Write-Host "DONE: monthly alert drill chain"
Write-Host "Drill summary: $drillSummary"
