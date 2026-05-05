# Wrapper for legacy scheduled task entrypoint.
# Purpose: keep existing Task Scheduler wiring alive by delegating to
# run_daily_prophecy_eval_and_report.ps1 and preserving key trinity safety flags.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$ProphecyTrinitySafetyWindow = 30,
    [int]$ProphecyTrinitySafetyConsecutiveThreshold = 3,
    [int]$RecentTradingDays = 30,
    [switch]$EnableWalkforwardAggregate,
    [int]$WalkforwardFolds = 6,
    [switch]$EnableOverlaySpike,
    [switch]$EnableCausalThresholdSweep,
    [switch]$SkipBuildScore,
    [switch]$EnableTrinityEvolution,
    [switch]$EnableRiskProfileSync,
    [string]$BtcCsvPath = "",
    [switch]$EnablePreNewsShadow,
    [switch]$EnablePreNewsShadowWeeklyReport,
    [string]$PreNewsBatchReportJson = "docs/final/artifacts/global_atom_full_canon_batch_report_latest.json",
    [string]$PreNewsInputJson = "docs/final/artifacts/pre_news_shadow_input_latest.json",
    [string]$PreNewsHoldoutReplayJson = "docs/final/artifacts/global_atom_news_network_holdout_replay_latest.json",
    [string]$PreNewsHoldoutDatasetLockJson = "docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_v1.json",
    [string]$PreNewsStageThresholdPolicyJson = "docs/final/artifacts/pre_news_shadow_stage_threshold_policy_v1.json",
    [int]$PreNewsPolicyAuditWindowDays = 30,
    [int]$PreNewsPolicyGovernanceAlertThreshold = 2,
    [int]$PreNewsPolicyChangeLogTailRows = 20
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$delegate = Join-Path $WorkspaceRoot "scripts\run_daily_prophecy_eval_and_report.ps1"
if (-not (Test-Path -LiteralPath $delegate)) {
    throw "Missing delegate script: $delegate"
}

$args = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $delegate,
    "-WorkspaceRoot", $WorkspaceRoot,
    "-RecentTradingDays", "$RecentTradingDays",
    "-TrinitySafetyWindow", "$ProphecyTrinitySafetyWindow",
    "-TrinitySafetyConsecutiveThreshold", "$ProphecyTrinitySafetyConsecutiveThreshold"
)
if ($SkipBuildScore) {
    $args += "-SkipBuildScore"
}
if (-not $EnableTrinityEvolution) {
    $args += "-SkipTrinityEvolution"
    $args += "-DisableAutoTrinitySafetyGate"
}
if (-not $EnableRiskProfileSync) {
    $args += "-SkipRiskProfileSync"
}
if ($EnableWalkforwardAggregate) {
    $args += @("-IncludeShadowPanelEval", "-ShadowPanelMode", "all")
    if ($WalkforwardFolds -gt 1) {
        $env:MKM_PROPHECY_WALKFORWARD_N_FOLDS = "$WalkforwardFolds"
    }
}
if ($EnableOverlaySpike) {
    $args += "-IncludeOverlaySpike"
}

# BTC leg input priority:
# 1) explicit -BtcCsvPath
# 2) env MKM_BTC_DAILY_CSV
# 3) research default
# 4) fixture fallback (keeps multi-instrument branch alive when real BTC feed is absent)
$btcCandidate = $null
if ($BtcCsvPath -and (Test-Path -LiteralPath $BtcCsvPath)) {
    $btcCandidate = $BtcCsvPath
}
elseif ($env:MKM_BTC_DAILY_CSV -and (Test-Path -LiteralPath $env:MKM_BTC_DAILY_CSV)) {
    $btcCandidate = $env:MKM_BTC_DAILY_CSV
}
else {
    $btcDefault = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
    $btcFixture = Join-Path $WorkspaceRoot "projects\bitcoin-trading\tests\fixtures\btc_smoke_daily.csv"
    if (Test-Path -LiteralPath $btcDefault) {
        $btcCandidate = $btcDefault
    }
    elseif (Test-Path -LiteralPath $btcFixture) {
        $btcCandidate = $btcFixture
        Write-Warning "Using BTC fixture fallback: $btcFixture (replace with real market feed for production-quality eval)."
    }
}
if ($btcCandidate) {
    $args += @("-BtcCsvPath", $btcCandidate)
}

& powershell.exe @args
$rc = $LASTEXITCODE
if ($rc -ne 0) {
    exit $rc
}

if ($EnableCausalThresholdSweep) {
    & py -3 "scripts\run_prophecy_causal_threshold_sweep_v1.py" `
        --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json" `
        --output "docs/final/artifacts/prophecy_causal_threshold_sweep_v1_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\build_prophecy_overlay_prior_threshold_recommended_from_causal_sweep_v1.py" `
        --sweep-json "docs/final/artifacts/prophecy_causal_threshold_sweep_v1_latest.json" `
        --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json" `
        --out "docs/final/artifacts/prophecy_overlay_prior_threshold_recommended_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    if ($EnableOverlaySpike) {
        $recPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_overlay_prior_threshold_recommended_latest.json"
        $scorePath = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_latest.json"
        $kospiPath = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"
        if ((Test-Path -LiteralPath $recPath) -and (Test-Path -LiteralPath $scorePath)) {
            try {
                $recObj = Get-Content -LiteralPath $recPath -Raw | ConvertFrom-Json
                $thr = [double]$recObj.recommended_prior_return_threshold
                & py -3 "scripts\run_prophecy_restoration_spike.py" `
                    --score-json $scorePath `
                    --kospi-csv $kospiPath `
                    --overlay prior_day_shock_bear_abstain_v0 `
                    --prior-return-threshold $thr `
                    --output "docs/final/artifacts/prophecy_restoration_spike_latest.json"
                if ($LASTEXITCODE -ne 0) {
                    exit $LASTEXITCODE
                }
            }
            catch {
                Write-Warning ("Failed to apply recommended overlay threshold from {0}: {1}" -f $recPath, $_.Exception.Message)
            }
        }
    }

    & py -3 "scripts\apply_prophecy_causal_best_to_score_v1.py" `
        --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json" `
        --sweep-json "docs/final/artifacts/prophecy_causal_threshold_sweep_v1_latest.json" `
        --report-out "docs/final/artifacts/prophecy_causal_active_apply_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\eval_prophecy_hit_rate_v1.py" `
        --run-mode price `
        --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json" `
        --out "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\resolve_prophecy_causal_guard_policy_profile_v1.py" `
        --profiles-json "docs/final/artifacts/prophecy_causal_active_guard_policy_profiles_v1_latest.json" `
        --eval-json "docs/final/artifacts/prophecy_hit_rate_eval_latest.json" `
        --walkforward-json "docs/final/artifacts/prophecy_instrument_combo_walkforward_v1_latest.json" `
        --out-policy-json "docs/final/artifacts/prophecy_causal_active_guard_policy_v1_latest.json" `
        --out-decision-json "docs/final/artifacts/prophecy_causal_active_guard_policy_decision_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\guard_prophecy_causal_active_hit_rate_v1.py" `
        --eval-json "docs/final/artifacts/prophecy_hit_rate_eval_latest.json" `
        --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json" `
        --backup-json "docs/final/artifacts/btrack_prophecy_score_pre_causal_active_latest.json" `
        --policy-json "docs/final/artifacts/prophecy_causal_active_guard_policy_v1_latest.json" `
        --out "docs/final/artifacts/prophecy_causal_active_guard_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    # If guard rolled back, recalculate final hit-rate on restored score.
    try {
        $guardPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_causal_active_guard_latest.json"
        if (Test-Path -LiteralPath $guardPath) {
            $guard = Get-Content -LiteralPath $guardPath -Raw | ConvertFrom-Json
            if ($guard.rolled_back -eq $true) {
                & py -3 "scripts\eval_prophecy_hit_rate_v1.py" `
                    --run-mode price `
                    --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json" `
                    --out "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
                if ($LASTEXITCODE -ne 0) {
                    exit $LASTEXITCODE
                }
            }
        }
    }
    catch {
        Write-Warning ("Guard post-check failed: {0}" -f $_.Exception.Message)
    }

    & py -3 "scripts\build_prophecy_causal_guard_policy_weekly_report_v1.py" `
        --decision-log-jsonl "reports/prophecy_causal_active_guard_policy_decision_log.jsonl" `
        --window-days 7 `
        --out "docs/final/artifacts/prophecy_causal_active_guard_policy_weekly_report_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\alert_prophecy_guard_profile_transition_v1.py" `
        --decision-json "docs/final/artifacts/prophecy_causal_active_guard_policy_decision_latest.json" `
        --state-json "docs/final/artifacts/prophecy_causal_active_guard_profile_state_latest.json" `
        --out-alert-json "docs/final/artifacts/prophecy_causal_active_guard_profile_transition_alert_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($EnablePreNewsShadow) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\run_global_atom_pre_news_shadow_chain_v1.ps1" `
        -BatchReportJson $PreNewsBatchReportJson `
        -PreNewsInputJson $PreNewsInputJson
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($EnablePreNewsShadowWeeklyReport) {
    & py -3 "scripts\build_global_atom_pre_news_shadow_weekly_report_v1.py" `
        --log-jsonl "reports/pre_news_shadow_projection_log.jsonl" `
        --holdout-replay-json $PreNewsHoldoutReplayJson `
        --holdout-dataset-lock-json $PreNewsHoldoutDatasetLockJson `
        --enforce-holdout-dataset-lock `
        --stage-threshold-policy-json $PreNewsStageThresholdPolicyJson `
        --enforce-policy-effective-from `
        --window-days 7 `
        --out-json "docs/final/artifacts/pre_news_shadow_weekly_report_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\build_pre_news_shadow_policy_change_audit_summary_v1.py" `
        --change-log-jsonl "reports/pre_news_shadow_stage_threshold_policy_change_log.jsonl" `
        --state-json "docs/final/artifacts/pre_news_shadow_stage_threshold_policy_state_latest.json" `
        --window-days $PreNewsPolicyAuditWindowDays `
        --out-json "docs/final/artifacts/pre_news_shadow_stage_threshold_policy_audit_summary_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\alert_pre_news_shadow_policy_governance_v1.py" `
        --audit-summary-json "docs/final/artifacts/pre_news_shadow_stage_threshold_policy_audit_summary_latest.json" `
        --out-alert-json "docs/final/artifacts/pre_news_shadow_policy_governance_alert_latest.json" `
        --append-alert-log-jsonl "reports/pre_news_shadow_policy_governance_alert_log.jsonl" `
        --change-count-threshold $PreNewsPolicyGovernanceAlertThreshold
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\build_pre_news_shadow_weekly_audit_bundle_v1.py" `
        --weekly-report-json "docs/final/artifacts/pre_news_shadow_weekly_report_latest.json" `
        --policy-audit-summary-json "docs/final/artifacts/pre_news_shadow_stage_threshold_policy_audit_summary_latest.json" `
        --policy-governance-alert-json "docs/final/artifacts/pre_news_shadow_policy_governance_alert_latest.json" `
        --policy-state-json "docs/final/artifacts/pre_news_shadow_stage_threshold_policy_state_latest.json" `
        --policy-change-log-jsonl "reports/pre_news_shadow_stage_threshold_policy_change_log.jsonl" `
        --holdout-replay-json $PreNewsHoldoutReplayJson `
        --holdout-lock-json $PreNewsHoldoutDatasetLockJson `
        --tail-policy-change-rows $PreNewsPolicyChangeLogTailRows `
        --out-json "docs/final/artifacts/pre_news_shadow_weekly_audit_bundle_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\build_pre_news_shadow_ops_status_dashboard_v1.py" `
        --weekly-report-json "docs/final/artifacts/pre_news_shadow_weekly_report_latest.json" `
        --policy-governance-alert-json "docs/final/artifacts/pre_news_shadow_policy_governance_alert_latest.json" `
        --task-health-alert-json "docs/final/artifacts/pre_news_shadow_task_health_alert_latest.json" `
        --weekly-audit-bundle-json "docs/final/artifacts/pre_news_shadow_weekly_audit_bundle_latest.json" `
        --weekly-audit-hash-manifest-json "docs/final/artifacts/pre_news_shadow_weekly_audit_bundle_hash_manifest_latest.json" `
        --holdout-lock-drill-json "docs/final/artifacts/pre_news_shadow_holdout_lock_mismatch_drill_latest.json" `
        --policy-governance-drill-json "docs/final/artifacts/pre_news_shadow_policy_governance_drill_latest.json" `
        --health-alert-drill-json "docs/final/artifacts/pre_news_shadow_alert_drill_latest.json" `
        --policy-alert-log-jsonl "reports/pre_news_shadow_policy_governance_alert_log.jsonl" `
        --task-health-alert-log-jsonl "reports/pre_news_shadow_task_health_alert_log.jsonl" `
        --projection-log-jsonl "reports/pre_news_shadow_projection_log.jsonl" `
        --tail-rows 5 `
        --out-json "docs/final/artifacts/pre_news_shadow_ops_status_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

exit 0
