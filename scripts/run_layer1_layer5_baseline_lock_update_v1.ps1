<#
.SYNOPSIS
  Controlled baseline-lock update chain (run only on approved governance window).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$SampleSize = 50,
    [int]$Seed = 42,
    [int]$MinApprovedSamples = 50
)

$ErrorActionPreference = "Stop"

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_layer1_layer5_governance_daily_v1.ps1") `
    -SampleSize $SampleSize `
    -Seed $Seed `
    -MinApprovedSamples $MinApprovedSamples `
    -UpdateBaselineLock
if ($LASTEXITCODE -ne 0) { throw "Governance chain with lock update failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_layer1_layer5_weekly_ops_report_v1.py") `
    --integrated-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_integrated_gate_report_latest.json") `
    --readiness-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_governance_readiness_latest.json") `
    --drift-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_baseline_drift_check_latest.json") `
    --slice-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_slice_benchmarks_latest.json") `
    --goldset-summary-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_incident_goldset_human_summary_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_ops_report_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Weekly ops report build failed ($LASTEXITCODE)" }

Write-Host "DONE: controlled baseline lock update chain"
