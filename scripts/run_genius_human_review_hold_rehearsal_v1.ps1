<#
.SYNOPSIS
  Run genius human-review HOLD rehearsal script.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $WorkspaceRoot "scripts\run_genius_human_review_hold_rehearsal_v1.py"
$outJson = Join-Path $WorkspaceRoot "docs\final\artifacts\genius_human_review_hold_rehearsal_latest.json"

& py $scriptPath --output-json $outJson
if ($LASTEXITCODE -ne 0) { throw "Genius human-review HOLD rehearsal failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_monthly_suite_status_v1.py") `
    --monthly-refresh-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --chaos-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_dispatch_chaos_drill_latest.json") `
    --hold-rehearsal-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_human_review_hold_rehearsal_latest.json") `
    --unified-dashboard-json (Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ai_unified_status_dashboard_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_monthly_suite_status_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius governance monthly suite status build failed ($LASTEXITCODE)" }

Write-Host "DONE: genius human-review HOLD rehearsal"
