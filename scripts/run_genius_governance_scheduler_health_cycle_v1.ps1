<#
.SYNOPSIS
  Run scheduler health cycle: check -> append history -> auto recovery -> dispatch alert.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$FastTransition
)

$ErrorActionPreference = "Stop"
$healthJson = Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_health_check_latest.json"
$healthHistory = Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_health_history_log.jsonl"
$modeSignalJson = Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_mode_signal_latest.json"

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_scheduler_health_check_v1.py") `
    --output-json $healthJson
if ($LASTEXITCODE -ne 0) { throw "Scheduler health check build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\append_genius_governance_scheduler_health_history_v1.py") `
    --health-json $healthJson `
    --history-jsonl $healthHistory
if ($LASTEXITCODE -ne 0) { throw "Scheduler health history append failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_scheduler_kpi_v1.py") `
    --health-history-jsonl $healthHistory `
    --recovery-history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_auto_recovery_history_log.jsonl") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_kpi_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Scheduler KPI build failed ($LASTEXITCODE)" }

 $stabilityMinPassRatio = 0.95
 $stabilityMaxHoldStreak = 1
 $stabilityMaxRecoveryAttempts = 2
 $completionMax24hHoldRecurrence = 0.0
 $completionMax24hRecoveryAttempts = 1
 if ($FastTransition) {
    # Fast transition mode: temporarily relax completion thresholds.
    $stabilityMinPassRatio = 0.85
    $stabilityMaxHoldStreak = 2
    $stabilityMaxRecoveryAttempts = 2
    $completionMax24hHoldRecurrence = 0.15
    $completionMax24hRecoveryAttempts = 1
 }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_scheduler_stability_48h_v1.py") `
    --health-history-jsonl $healthHistory `
    --recovery-history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_auto_recovery_history_log.jsonl") `
    --window-hours 48 `
    --min-pass-ratio $stabilityMinPassRatio `
    --max-hold-streak $stabilityMaxHoldStreak `
    --max-recovery-attempts $stabilityMaxRecoveryAttempts `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_stability_48h_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Scheduler 48h stability build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_scheduler_mode_signal_v1.py") `
    --stability-48h-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_stability_48h_latest.json") `
    --health-json $healthJson `
    --output-json $modeSignalJson
if ($LASTEXITCODE -ne 0) { throw "Scheduler mode signal build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_completion_gate_v1.py") `
    --stability-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_stability_48h_latest.json") `
    --kpi-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_kpi_latest.json") `
    --max-24h-hold-recurrence $completionMax24hHoldRecurrence `
    --max-24h-recovery-attempts $completionMax24hRecoveryAttempts `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_gate_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Completion gate build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\dispatch_genius_governance_completion_24h_alert_v1.py") `
    --completion-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_gate_latest.json") `
    --health-history-jsonl $healthHistory `
    --state-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_24h_alert_state_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_24h_alert_dispatch_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Completion 24h alert dispatch failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_completion_eta_v1.py") `
    --completion-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_gate_latest.json") `
    --health-history-jsonl $healthHistory `
    --required-hours 24 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_completion_eta_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Completion ETA build failed ($LASTEXITCODE)" }

$mode = "OBSERVE_MODE"
if (Test-Path -LiteralPath $modeSignalJson) {
    $modeDoc = Get-Content -LiteralPath $modeSignalJson -Raw | ConvertFrom-Json
    if ($null -ne $modeDoc.mode_signal.mode) {
        $mode = [string]$modeDoc.mode_signal.mode
    }
}

$recoveryHoldStreakThreshold = 2
$recoveryCooldownMinutes = 120
$alertMinHoldStreakToDispatch = 2
if ($mode -eq "TUNING_MODE") {
    # Tuning mode: recover faster and alert earlier.
    $recoveryHoldStreakThreshold = 1
    $recoveryCooldownMinutes = 30
    $alertMinHoldStreakToDispatch = 1
}

& py (Join-Path $WorkspaceRoot "scripts\run_genius_governance_scheduler_auto_recovery_v1.py") `
    --health-history-jsonl $healthHistory `
    --recovery-history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_auto_recovery_history_log.jsonl") `
    --hold-streak-threshold $recoveryHoldStreakThreshold `
    --cooldown-minutes $recoveryCooldownMinutes `
    --recovery-task-name "\MKM_GeniusHumanReview_HoldRehearsal_Monthly" `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_auto_recovery_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Scheduler auto recovery step failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\dispatch_genius_governance_scheduler_health_alert_v1.py") `
    --health-json $healthJson `
    --history-jsonl $healthHistory `
    --min-hold-streak-to-dispatch $alertMinHoldStreakToDispatch `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_scheduler_health_alert_dispatch_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Scheduler health alert dispatch step failed ($LASTEXITCODE)" }

Write-Host "DONE: genius governance scheduler health cycle"
