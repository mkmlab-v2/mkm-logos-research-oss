<#
.SYNOPSIS
  Run completion gate + weekly scorecard + end-to-end forced hold rehearsal.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_genius_governance_scheduler_health_cycle_v1.ps1") -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) { throw "Health cycle failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_completion_gate_v1.py") `
    --stability-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_stability_48h_latest.json") `
    --kpi-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_kpi_latest.json") `
    --max-24h-hold-recurrence 0.0 `
    --max-24h-recovery-attempts 1 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_gate_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Completion gate build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_weekly_scorecard_v1.py") `
    --kpi-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_kpi_latest.json") `
    --mode-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_mode_signal_latest.json") `
    --recovery-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_auto_recovery_latest.json") `
    --alert-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_health_alert_dispatch_latest.json") `
    --completion-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_gate_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_weekly_scorecard_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Weekly scorecard build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\dispatch_genius_governance_completion_24h_alert_v1.py") `
    --completion-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_gate_latest.json") `
    --health-history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_health_history_log.jsonl") `
    --state-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_24h_alert_state_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_24h_alert_dispatch_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Completion 24h alert dispatch failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\run_genius_governance_scheduler_forced_hold_drill_v1.py") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_forced_hold_drill_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Forced hold rehearsal failed ($LASTEXITCODE)" }

Write-Host "DONE: genius governance completion + rehearsal"
