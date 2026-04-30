<#
.SYNOPSIS
  Weekly maintenance chain for Layer1/Layer5 governance.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$SampleSize = 50,
    [int]$Seed = 42,
    [int]$MinApprovedSamples = 50
)

$ErrorActionPreference = "Stop"
$profileOut = Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ai_operating_profile_v1_latest.json"
$requiredStreak = 4
if (Test-Path -LiteralPath $profileOut) {
    $profile = Get-Content -LiteralPath $profileOut -Raw | ConvertFrom-Json
    if ($null -ne $profile.gates.required_weekly_streak) {
        $requiredStreak = [int]$profile.gates.required_weekly_streak
    }
}
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

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_layer1_layer5_governance_daily_v1.ps1") `
    -SampleSize $SampleSize `
    -Seed $Seed `
    -MinApprovedSamples $MinApprovedSamples
if ($LASTEXITCODE -ne 0) { throw "Daily governance chain failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\run_layer5_slice_benchmarks_v1.py") `
    --goldset-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_incident_goldset_human_v1_latest.jsonl") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_slice_benchmarks_latest.json") `
    --slice-size 30 `
    --seed $Seed
if ($LASTEXITCODE -ne 0) { throw "Slice benchmark chain failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\export_layer5_new_draft_review_batch_v1.py") `
    --queue-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_incident_review_queue_v1_latest.jsonl") `
    --output-csv (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_new_draft_review_batch_ids_v1.csv") `
    --summary-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_new_draft_review_batch_summary_latest.json") `
    --batch-size 30
if ($LASTEXITCODE -ne 0) { throw "New draft review batch export failed ($LASTEXITCODE)" }

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_agent_memory_weekly_rebuild_v1.ps1") `
    -WorkspaceRoot $WorkspaceRoot `
    -TtlDays 7
if ($LASTEXITCODE -ne 0) { throw "Agent memory weekly rebuild chain failed ($LASTEXITCODE)" }

# Build Sasang microcosm runtime assessment for weekly report/dashboard.
& py (Join-Path $WorkspaceRoot "scripts\build_sasang_microcosm_control_bundle_v1.py") `
    --output-bundle-json (Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_microcosm_control_bundle_v1_latest.json") `
    --output-runtime-json (Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_microcosm_runtime_assessment_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Sasang microcosm bundle/runtime build failed ($LASTEXITCODE)" }

# Rebuild external baseline latest index so tiering always gets valid artifact pointers.
& py (Join-Path $WorkspaceRoot "scripts\build_external_baseline_latest_index_v1.py") `
    --comparison-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_overlap_comparison_latest.json") `
    --dual-mode-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_dual_mode_report_latest.json") `
    --exploration-brief-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_exploration_signal_brief_latest.json") `
    --human-review-queue-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_human_review_queue_latest.json") `
    --human-review-resolution-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_human_review_resolution_latest.json") `
    --threshold-tuning-proposal-json (Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_external_baseline_threshold_tuning_proposal_latest.json") `
    --threshold-apply-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_threshold_apply_gate_latest.json") `
    --threshold-apply-approval-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_threshold_apply_approval_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_latest_index.json")
if ($LASTEXITCODE -ne 0) { throw "External baseline latest index build failed ($LASTEXITCODE)" }

# Build external baseline anchor tiering policy (hypothesis pool gating).
& py (Join-Path $WorkspaceRoot "scripts\build_external_bible_anchor_tiering_v1.py") `
    --index-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_latest_index.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor tiering build failed ($LASTEXITCODE)" }

# Build adopt_limited rehearsal readiness from tiering + apply gates.
& py (Join-Path $WorkspaceRoot "scripts\build_external_anchor_adopt_limited_rehearsal_v1.py") `
    --tiering-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json") `
    --apply-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_threshold_apply_gate_latest.json") `
    --apply-approval-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_threshold_apply_approval_latest.json") `
    --core100-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\core100_node_ref_map_quality_gate_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_adopt_limited_rehearsal_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor adopt_limited rehearsal build failed ($LASTEXITCODE)" }

# Build tier2 shadow rehearsal result.
& py (Join-Path $WorkspaceRoot "scripts\build_external_anchor_shadow_rehearsal_v1.py") `
    --tiering-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json") `
    --rehearsal-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_adopt_limited_rehearsal_latest.json") `
    --comparison-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_overlap_comparison_latest.json") `
    --min-shadow-uplift 0.001 `
    --target-candidate-pool 5 `
    --target-shadow-pass-count 3 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_shadow_rehearsal_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor shadow rehearsal build failed ($LASTEXITCODE)" }

# Build tier1 promotion candidate proposal from shadow pass.
& py (Join-Path $WorkspaceRoot "scripts\build_external_anchor_tier1_promotion_candidates_v1.py") `
    --shadow-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_shadow_rehearsal_latest.json") `
    --apply-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_threshold_apply_gate_latest.json") `
    --threshold-proposal-json (Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_external_baseline_threshold_tuning_proposal_latest.json") `
    --target-min-candidates 3 `
    --target-max-candidates 5 `
    --relaxed-delta-floor 0.0 `
    --relaxed-precision-floor 0.0 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promotion_candidates_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor tier1 promotion candidate build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\promote_external_anchor_tier1_candidates_v1.py") `
    --candidates-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promotion_candidates_latest.json") `
    --signoff-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_manual_signoff_latest.json") `
    --apply-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_crossref_threshold_apply_gate_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor tier1 promotion apply failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_external_anchor_post_promotion_regression_v1.py") `
    --promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --shadow-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_shadow_rehearsal_latest.json") `
    --layer5-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_policy_gate_benchmark_latest.json") `
    --preflight-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_live_preflight_gate_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_post_promotion_regression_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor post-promotion regression check failed ($LASTEXITCODE)" }

# Sustain gate from existing history (before this run's append), then sync so strict threshold uses fresh sustain.
& py (Join-Path $WorkspaceRoot "scripts\check_external_anchor_promotion_sustain_gate_v1.py") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_history_log.jsonl") `
    --required-pass-streak 3 `
    --required-fail-streak-for-downgrade 2 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor promotion sustain gate failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\sync_external_anchor_tier1_into_operating_policy_v1.py") `
    --tiering-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json") `
    --promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --regression-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_post_promotion_regression_latest.json") `
    --sustain-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json") `
    --strict-pass-streak-threshold 6 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_operating_policy_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor operating policy sync failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\append_external_anchor_promotion_history_v1.py") `
    --promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --policy-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_operating_policy_latest.json") `
    --regression-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_post_promotion_regression_latest.json") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_history_log.jsonl")
if ($LASTEXITCODE -ne 0) { throw "External anchor promotion history append failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_external_anchor_promotion_sustain_gate_v1.py") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_history_log.jsonl") `
    --required-pass-streak 3 `
    --required-fail-streak-for-downgrade 2 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor promotion sustain gate (post-append) failed ($LASTEXITCODE)" }

# Build recovery candidate proposal only when sustain gate is downgrade-triggered.
& py (Join-Path $WorkspaceRoot "scripts\build_external_anchor_recovery_candidates_v1.py") `
    --sustain-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json") `
    --shadow-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_shadow_rehearsal_latest.json") `
    --current-candidates-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promotion_candidates_latest.json") `
    --target-candidates 3 `
    --max-overlap-with-current 1 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_recovery_candidates_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor recovery candidate build failed ($LASTEXITCODE)" }

# Final sync: sustain JSON now includes this run's history row (strict streak includes adopt_limited_strict weeks).
& py (Join-Path $WorkspaceRoot "scripts\sync_external_anchor_tier1_into_operating_policy_v1.py") `
    --tiering-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json") `
    --promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --regression-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_post_promotion_regression_latest.json") `
    --sustain-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json") `
    --strict-pass-streak-threshold 6 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_operating_policy_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor operating policy final sync failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\append_external_anchor_promotion_history_v1.py") `
    --promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --policy-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_operating_policy_latest.json") `
    --regression-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_post_promotion_regression_latest.json") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_history_log.jsonl") `
    --overwrite-last-row
if ($LASTEXITCODE -ne 0) { throw "External anchor promotion history finalize failed ($LASTEXITCODE)" }

# Build weekly A/B report for adopt_limited vs monitor_only evidence.
& py (Join-Path $WorkspaceRoot "scripts\build_external_anchor_weekly_ab_report_v1.py") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_history_log.jsonl") `
    --preflight-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_live_preflight_gate_latest.json") `
    --layer5-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_policy_gate_benchmark_latest.json") `
    --sustain-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json") `
    --window 12 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_weekly_ab_report_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor weekly A/B report build failed ($LASTEXITCODE)" }

# Run policy stage transition drill (limited/strict/monitor) for governance evidence.
& py (Join-Path $WorkspaceRoot "scripts\run_external_anchor_policy_stage_drill_v1.py") `
    --tiering-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json") `
    --promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --regression-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_post_promotion_regression_latest.json") `
    --strict-pass-streak-threshold 6 `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_policy_stage_drill_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor policy stage drill failed ($LASTEXITCODE)" }

# Build one-file handoff packet for next human/automation decision.
& py (Join-Path $WorkspaceRoot "scripts\build_external_anchor_promotion_handoff_packet_v1.py") `
    --promotion-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promotion_candidates_latest.json") `
    --promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --recovery-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_recovery_candidates_latest.json") `
    --sustain-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json") `
    --policy-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_operating_policy_latest.json") `
    --weekly-ab-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_weekly_ab_report_latest.json") `
    --policy-stage-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_policy_stage_drill_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_handoff_packet_latest.json")
if ($LASTEXITCODE -ne 0) { throw "External anchor promotion handoff packet build failed ($LASTEXITCODE)" }

# Build symbolic-reality-meta blend runtime policy.
& py (Join-Path $WorkspaceRoot "scripts\build_symbolic_reality_blend_runtime_v1.py") `
    --mode auto `
    --integrated-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_integrated_gate_report_latest.json") `
    --preflight-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_live_preflight_gate_latest.json") `
    --microcosm-json (Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_microcosm_runtime_assessment_latest.json") `
    --profile-json (Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ai_operating_profile_v1_latest.json") `
    --anchor-tiering-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json") `
    --anchor-operating-policy-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_operating_policy_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\symbolic_reality_blend_runtime_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Symbolic-reality blend runtime build failed ($LASTEXITCODE)" }

# Build genius-style reasoning benchmark artifact.
& py (Join-Path $WorkspaceRoot "scripts\run_genius_reasoning_benchmark_v1.py") `
    --weekly-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_ops_report_latest.json") `
    --microcosm-json (Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_microcosm_runtime_assessment_latest.json") `
    --tasks-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_tasks_v1.json") `
    --min-safety-score $minSafetyScore `
    --min-long-horizon-score $minLongHorizonScore `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius reasoning benchmark build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_genius_reasoning_benchmark_alert_v1.py") `
    --benchmark-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius reasoning benchmark alert build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\dispatch_genius_reasoning_alert_webhook_v1.py") `
    --alert-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_dispatch_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius reasoning benchmark alert dispatch failed ($LASTEXITCODE)" }

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

& py (Join-Path $WorkspaceRoot "scripts\append_genius_reasoning_alert_history_v1.py") `
    --alert-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_latest.json") `
    --benchmark-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_history_log.jsonl")
if ($LASTEXITCODE -ne 0) { throw "Genius reasoning benchmark alert history append failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_genius_reasoning_alert_trend_gate_v1.py") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_history_log.jsonl") `
    --window $alertTrendWindow `
    --max-warning-count $alertTrendMaxWarning `
    --max-critical-count $alertTrendMaxCritical `
    --max-active-ratio $alertTrendMaxActiveRatio `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_trend_gate_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Genius reasoning benchmark alert trend gate failed ($LASTEXITCODE)" }

# Build preliminary weekly report (without updated streak history yet).
& py (Join-Path $WorkspaceRoot "scripts\build_layer1_layer5_weekly_ops_report_v1.py") `
    --integrated-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_integrated_gate_report_latest.json") `
    --readiness-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_governance_readiness_latest.json") `
    --drift-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_baseline_drift_check_latest.json") `
    --slice-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_slice_benchmarks_latest.json") `
    --goldset-summary-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_incident_goldset_human_summary_latest.json") `
    --emotion-promotion-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_promotion_gate_latest.json") `
    --emotion-promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_track_a_promoted_latest.json") `
    --emotion-preflight-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_live_preflight_gate_latest.json") `
    --memory-validation-json (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_validation_latest.json") `
    --memory-rebuild-json (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_weekly_rebuild_summary_latest.json") `
    --streak-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_streak_gate_latest.json") `
    --microcosm-runtime-json (Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_microcosm_runtime_assessment_latest.json") `
    --genius-benchmark-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --genius-alert-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_latest.json") `
    --genius-alert-trend-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_trend_gate_latest.json") `
    --genius-human-review-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_latest.json") `
    --genius-human-review-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_dispatch_latest.json") `
    --genius-human-review-trend-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_latest.json") `
    --genius-human-review-trend-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_dispatch_latest.json") `
    --genius-dispatch-health-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_gate_latest.json") `
    --genius-dispatch-health-gate-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_gate_dispatch_latest.json") `
    --blend-runtime-json (Join-Path $WorkspaceRoot "docs\final\artifacts\symbolic_reality_blend_runtime_latest.json") `
    --anchor-tiering-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json") `
    --anchor-rehearsal-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_adopt_limited_rehearsal_latest.json") `
    --anchor-shadow-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_shadow_rehearsal_latest.json") `
    --anchor-promotion-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promotion_candidates_latest.json") `
    --anchor-promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --anchor-sustain-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json") `
    --anchor-recovery-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_recovery_candidates_latest.json") `
    --anchor-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_downgrade_recovery_drill_latest.json") `
    --anchor-weekly-ab-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_weekly_ab_report_latest.json") `
    --anchor-policy-stage-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_policy_stage_drill_latest.json") `
    --anchor-handoff-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_handoff_packet_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_ops_report_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Preliminary weekly ops report failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\append_layer1_layer5_weekly_ops_history_v1.py") `
    --weekly-report-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_ops_report_latest.json") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_ops_history_log.jsonl")
if ($LASTEXITCODE -ne 0) { throw "Weekly history append failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_layer1_layer5_weekly_streak_gate_v1.py") `
    --history-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_ops_history_log.jsonl") `
    --required-streak $requiredStreak `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_streak_gate_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Weekly streak gate check failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_layer1_layer5_weekly_ops_report_v1.py") `
    --integrated-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_integrated_gate_report_latest.json") `
    --readiness-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_governance_readiness_latest.json") `
    --drift-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_baseline_drift_check_latest.json") `
    --slice-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_slice_benchmarks_latest.json") `
    --goldset-summary-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_incident_goldset_human_summary_latest.json") `
    --emotion-promotion-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_promotion_gate_latest.json") `
    --emotion-promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_track_a_promoted_latest.json") `
    --emotion-preflight-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_live_preflight_gate_latest.json") `
    --memory-validation-json (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_validation_latest.json") `
    --memory-rebuild-json (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_weekly_rebuild_summary_latest.json") `
    --streak-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_streak_gate_latest.json") `
    --microcosm-runtime-json (Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_microcosm_runtime_assessment_latest.json") `
    --genius-benchmark-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --genius-alert-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_latest.json") `
    --genius-alert-trend-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_trend_gate_latest.json") `
    --genius-human-review-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_latest.json") `
    --genius-human-review-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_dispatch_latest.json") `
    --genius-human-review-trend-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_latest.json") `
    --genius-human-review-trend-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_dispatch_latest.json") `
    --genius-dispatch-health-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_gate_latest.json") `
    --genius-dispatch-health-gate-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_gate_dispatch_latest.json") `
    --blend-runtime-json (Join-Path $WorkspaceRoot "docs\final\artifacts\symbolic_reality_blend_runtime_latest.json") `
    --anchor-tiering-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json") `
    --anchor-rehearsal-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_adopt_limited_rehearsal_latest.json") `
    --anchor-shadow-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_shadow_rehearsal_latest.json") `
    --anchor-promotion-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promotion_candidates_latest.json") `
    --anchor-promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --anchor-sustain-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json") `
    --anchor-recovery-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_recovery_candidates_latest.json") `
    --anchor-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_downgrade_recovery_drill_latest.json") `
    --anchor-weekly-ab-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_weekly_ab_report_latest.json") `
    --anchor-policy-stage-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_policy_stage_drill_latest.json") `
    --anchor-handoff-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_handoff_packet_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_ops_report_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Weekly ops report failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_cursor_ai_unified_status_dashboard_v1.py") `
    --weekly-report-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_ops_report_latest.json") `
    --preflight-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_live_preflight_gate_latest.json") `
    --memory-validation-json (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_validation_latest.json") `
    --memory-rebuild-json (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_weekly_rebuild_summary_latest.json") `
    --streak-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_weekly_streak_gate_latest.json") `
    --microcosm-runtime-json (Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_microcosm_runtime_assessment_latest.json") `
    --genius-benchmark-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_report_latest.json") `
    --genius-alert-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_latest.json") `
    --genius-alert-trend-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_benchmark_alert_trend_gate_latest.json") `
    --genius-human-review-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_latest.json") `
    --genius-human-review-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_dispatch_latest.json") `
    --genius-human-review-trend-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_latest.json") `
    --genius-human-review-trend-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_human_review_gate_trend_dispatch_latest.json") `
    --genius-dispatch-health-gate-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_gate_latest.json") `
    --genius-dispatch-health-gate-dispatch-json (Join-Path $WorkspaceRoot "docs\final\artifacts\genius_reasoning_dispatch_health_gate_dispatch_latest.json") `
    --blend-runtime-json (Join-Path $WorkspaceRoot "docs\final\artifacts\symbolic_reality_blend_runtime_latest.json") `
    --anchor-tiering-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tiering_latest.json") `
    --anchor-rehearsal-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_adopt_limited_rehearsal_latest.json") `
    --anchor-shadow-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_shadow_rehearsal_latest.json") `
    --anchor-promotion-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promotion_candidates_latest.json") `
    --anchor-promoted-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_tier1_promoted_latest.json") `
    --anchor-sustain-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_sustain_gate_latest.json") `
    --anchor-recovery-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_recovery_candidates_latest.json") `
    --anchor-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_downgrade_recovery_drill_latest.json") `
    --anchor-weekly-ab-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_weekly_ab_report_latest.json") `
    --anchor-policy-stage-drill-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_policy_stage_drill_latest.json") `
    --anchor-handoff-json (Join-Path $WorkspaceRoot "docs\final\artifacts\external_bible_anchor_promotion_handoff_packet_latest.json") `
    --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ai_unified_status_dashboard_latest.json")
if ($LASTEXITCODE -ne 0) { throw "Unified status dashboard build failed ($LASTEXITCODE)" }

Write-Host "DONE: weekly Layer1/Layer5 maintenance chain"
