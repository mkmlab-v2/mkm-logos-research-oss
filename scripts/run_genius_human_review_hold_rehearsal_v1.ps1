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

function Invoke-WithRetry {
    param(
        [scriptblock]$Action,
        [string]$Label,
        [int]$MaxAttempts = 3,
        [int]$DelaySeconds = 2
    )
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        & $Action
        if ($LASTEXITCODE -eq 0) { return }
        if ($attempt -lt $MaxAttempts) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }
    throw "$Label failed after $MaxAttempts attempts (last exit=$LASTEXITCODE)"
}

Invoke-WithRetry -Label "Genius human-review HOLD rehearsal" -Action {
    & py $scriptPath --output-json $outJson
}

Invoke-WithRetry -Label "Genius governance monthly suite status build" -Action {
    & py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_monthly_suite_status_v1.py") `
        --monthly-refresh-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
        --chaos-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_dispatch_chaos_drill_latest.json") `
        --hold-rehearsal-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_human_review_hold_rehearsal_latest.json") `
        --unified-dashboard-json (Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ai_unified_status_dashboard_latest.json") `
        --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_monthly_suite_status_latest.json")
}

Write-Host "DONE: genius human-review HOLD rehearsal"
