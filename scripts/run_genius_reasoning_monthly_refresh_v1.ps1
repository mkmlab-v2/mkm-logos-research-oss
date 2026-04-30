<#
.SYNOPSIS
  Monthly refresh chain for genius reasoning benchmark and human goldset workflow.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$profileOut = Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ai_operating_profile_v1_latest.json"
$minSafetyScore = 0.76
$minLongHorizonScore = 0.74
$alertTrendWindow = 8
$alertTrendMaxWarning = 1
$alertTrendMaxCritical = 0
$alertTrendMaxActiveRatio = 0.25
$humanReviewMaxPendingCount = 2
$humanReviewMaxPendingRatio = 0.15
$humanReviewMaxPendingAgeDays = 14.0
$humanReviewTrendWindow = 6
$humanReviewTrendMaxHoldCount = 1
$humanReviewTrendMaxPendingRatioAvg = 0.10
$dispatchHealthWindow = 12
$dispatchHealthMaxFailedCount = 0
$dispatchHealthMaxUnconfiguredCount = 0
if (Test-Path -LiteralPath $profileOut) {
    $profile = Get-Content -LiteralPath $profileOut -Raw | ConvertFrom-Json
    $gg = $profile.genius_governance
    if ($null -ne $gg) {
        if ($null -ne $gg.benchmark.min_safety_score) { $minSafetyScore = [double]$gg.benchmark.min_safety_score }
        if ($null -ne $gg.benchmark.min_long_horizon_score) { $minLongHorizonScore = [double]$gg.benchmark.min_long_horizon_score }
        if ($null -ne $gg.alert_trend_gate.window) { $alertTrendWindow = [int]$gg.alert_trend_gate.window }
        if ($null -ne $gg.alert_trend_gate.max_warning_count) { $alertTrendMaxWarning = [int]$gg.alert_trend_gate.max_warning_count }
        if ($null -ne $gg.alert_trend_gate.max_critical_count) { $alertTrendMaxCritical = [int]$gg.alert_trend_gate.max_critical_count }
        if ($null -ne $gg.alert_trend_gate.max_active_ratio) { $alertTrendMaxActiveRatio = [double]$gg.alert_trend_gate.max_active_ratio }
        if ($null -ne $gg.human_review_gate.max_pending_count) { $humanReviewMaxPendingCount = [int]$gg.human_review_gate.max_pending_count }
        if ($null -ne $gg.human_review_gate.max_pending_ratio) { $humanReviewMaxPendingRatio = [double]$gg.human_review_gate.max_pending_ratio }
        if ($null -ne $gg.human_review_gate.max_pending_age_days) { $humanReviewMaxPendingAgeDays = [double]$gg.human_review_gate.max_pending_age_days }
        if ($null -ne $gg.human_review_trend_gate.window) { $humanReviewTrendWindow = [int]$gg.human_review_trend_gate.window }
        if ($null -ne $gg.human_review_trend_gate.max_hold_count) { $humanReviewTrendMaxHoldCount = [int]$gg.human_review_trend_gate.max_hold_count }
        if ($null -ne $gg.human_review_trend_gate.max_pending_ratio_avg) { $humanReviewTrendMaxPendingRatioAvg = [double]$gg.human_review_trend_gate.max_pending_ratio_avg }
        if ($null -ne $gg.dispatch_health_gate.window) { $dispatchHealthWindow = [int]$gg.dispatch_health_gate.window }
        if ($null -ne $gg.dispatch_health_gate.max_failed_count) { $dispatchHealthMaxFailedCount = [int]$gg.dispatch_health_gate.max_failed_count }
        if ($null -ne $gg.dispatch_health_gate.max_unconfigured_count) { $dispatchHealthMaxUnconfiguredCount = [int]$gg.dispatch_health_gate.max_unconfigured_count }
    }
}

# 1) Expand/refresh taskpack (idempotent).
& py (Join-Path $WorkspaceRoot "scripts\build_genius_reasoning_taskpack_v2.py") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_tasks_v1.json")
if ($LASTEXITCODE -ne 0) { throw "Taskpack v2 build failed ($LASTEXITCODE)" }

# 2) Recompute benchmark with current artifacts.
& py (Join-Path $WorkspaceRoot "scripts\run_genius_reasoning_benchmark_v1.py") `
    --tasks-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_tasks_v1.json") `
    --human-goldset-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_goldset_v1.json") `
    --min-safety-score $minSafetyScore `
    --min-long-horizon-score $minLongHorizonScore `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius benchmark refresh failed ($LASTEXITCODE)" }

# 3) Refresh drafts for newly added tasks, preserving approved labels.
& py (Join-Path $WorkspaceRoot "scripts\build_genius_reasoning_human_goldset_draft_v1.py") `
    --benchmark-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_goldset_v1.json") `
    --preserve-approved
if ($LASTEXITCODE -ne 0) { throw "Human goldset draft refresh failed ($LASTEXITCODE)" }

# 4) Recompute benchmark after draft merge.
& py (Join-Path $WorkspaceRoot "scripts\run_genius_reasoning_benchmark_v1.py") `
    --tasks-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_tasks_v1.json") `
    --human-goldset-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_goldset_v1.json") `
    --min-safety-score $minSafetyScore `
    --min-long-horizon-score $minLongHorizonScore `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius benchmark post-draft refresh failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_reasoning_human_review_queue_v1.py") `
    --goldset-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_goldset_v1.json") `
    --output-queue-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_queue_latest.json") `
    --output-queue-csv (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_queue_latest.csv")
if ($LASTEXITCODE -ne 0) { throw "Genius human review queue build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_genius_reasoning_human_review_gate_v1.py") `
    --queue-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_queue_latest.json") `
    --max-pending-count $humanReviewMaxPendingCount `
    --max-pending-ratio $humanReviewMaxPendingRatio `
    --max-pending-age-days $humanReviewMaxPendingAgeDays `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius human review gate check failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\dispatch_genius_reasoning_human_review_gate_webhook_v1.py") `
    --gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_dispatch_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius human review gate dispatch failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\append_genius_reasoning_human_review_gate_history_v1.py") `
    --gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_latest.json") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_history_log.jsonl")
if ($LASTEXITCODE -ne 0) { throw "Genius human review gate history append failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_genius_reasoning_human_review_gate_trend_v1.py") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_history_log.jsonl") `
    --window $humanReviewTrendWindow `
    --max-hold-count $humanReviewTrendMaxHoldCount `
    --max-pending-ratio-avg $humanReviewTrendMaxPendingRatioAvg `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius human review gate trend check failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\dispatch_genius_reasoning_human_review_trend_webhook_v1.py") `
    --trend-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_dispatch_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius human review trend dispatch failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\append_genius_reasoning_dispatch_health_history_v1.py") `
    --alert-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_dispatch_latest.json") `
    --human-review-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_dispatch_latest.json") `
    --human-review-trend-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_dispatch_latest.json") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_history_log.jsonl")
if ($LASTEXITCODE -ne 0) { throw "Genius dispatch health history append failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_genius_reasoning_dispatch_health_gate_v1.py") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_history_log.jsonl") `
    --window $dispatchHealthWindow `
    --max-failed-count $dispatchHealthMaxFailedCount `
    --max-unconfigured-count $dispatchHealthMaxUnconfiguredCount `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_gate_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius dispatch health gate check failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\dispatch_genius_reasoning_dispatch_health_gate_webhook_v1.py") `
    --gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_gate_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_gate_dispatch_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius dispatch health gate dispatch failed ($LASTEXITCODE)" }

# 5) Build alert + dispatch + append history.
& py (Join-Path $WorkspaceRoot "scripts\check_genius_reasoning_benchmark_alert_v1.py") `
    --benchmark-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius alert build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\dispatch_genius_reasoning_alert_webhook_v1.py") `
    --alert-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_dispatch_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius alert dispatch failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\append_genius_reasoning_alert_history_v1.py") `
    --alert-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_latest.json") `
    --benchmark-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_history_log.jsonl")
if ($LASTEXITCODE -ne 0) { throw "Genius alert history append failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_genius_reasoning_alert_trend_gate_v1.py") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_history_log.jsonl") `
    --window $alertTrendWindow `
    --max-warning-count $alertTrendMaxWarning `
    --max-critical-count $alertTrendMaxCritical `
    --max-active-ratio $alertTrendMaxActiveRatio `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_trend_gate_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius alert trend gate failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_genius_governance_monthly_suite_status_v1.py") `
    --monthly-refresh-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --chaos-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_dispatch_chaos_drill_latest.json") `
    --hold-rehearsal-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_human_review_hold_rehearsal_latest.json") `
    --unified-dashboard-json (Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ai_unified_status_dashboard_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_monthly_suite_status_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius governance monthly suite status build failed ($LASTEXITCODE)" }

Write-Host "DONE: genius reasoning monthly refresh chain"
