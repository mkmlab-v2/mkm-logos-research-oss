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
    [switch]$OperationModeBShadow,
    [switch]$EnablePreNewsShadow,
    [switch]$SkipNaverNewsIngest,
    [switch]$SkipExaMacroNewsRefresh,
    [switch]$SkipExternalFeedRefresh,
    [string]$ExternalNewsFeedJson = "docs/final/artifacts/external_feed_drop_latest.validated.json",
    [switch]$EnablePreNewsShadowWeeklyReport,
    [string]$PreNewsBatchReportJson = "docs/final/artifacts/global_atom_full_canon_batch_report_latest.json",
    [string]$PreNewsInputJson = "docs/final/artifacts/pre_news_shadow_input_latest.json",
    [string]$PreNewsHoldoutReplayJson = "docs/final/artifacts/global_atom_news_network_holdout_replay_latest.json",
    [string]$PreNewsHoldoutDatasetLockJson = "docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_v1.json",
    [string]$PreNewsStageThresholdPolicyJson = "docs/final/artifacts/pre_news_shadow_stage_threshold_policy_v1.json",
    [int]$PreNewsPolicyAuditWindowDays = 30,
    [int]$PreNewsPolicyGovernanceAlertThreshold = 2,
    [int]$PreNewsPolicyChangeLogTailRows = 20,
    [switch]$SkipLiveProphecyTriage,
    [switch]$SkipBiblicalHistoryChronicleRefresh
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
if ($OperationModeBShadow) {
    $args += "-OperationModeBShadow"
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
        --output "docs/final/artifacts/prophecy_hit_rate_eval_daily_operational_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\resolve_prophecy_causal_guard_policy_profile_v1.py" `
        --profiles-json "docs/final/artifacts/prophecy_causal_active_guard_policy_profiles_v1_latest.json" `
        --eval-json "docs/final/artifacts/prophecy_hit_rate_eval_daily_operational_latest.json" `
        --walkforward-json "docs/final/artifacts/prophecy_instrument_combo_walkforward_v1_latest.json" `
        --out-policy-json "docs/final/artifacts/prophecy_causal_active_guard_policy_v1_latest.json" `
        --out-decision-json "docs/final/artifacts/prophecy_causal_active_guard_policy_decision_latest.json"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & py -3 "scripts\guard_prophecy_causal_active_hit_rate_v1.py" `
        --eval-json "docs/final/artifacts/prophecy_hit_rate_eval_daily_operational_latest.json" `
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
                    --output "docs/final/artifacts/prophecy_hit_rate_eval_daily_operational_latest.json"
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
    if (-not $SkipNaverNewsIngest) {
        Write-Host "==> fetch_naver_openapi_signals_v1.py (pre-news upstream ingest)" -ForegroundColor Cyan
        & py -3 "scripts\fetch_naver_openapi_signals_v1.py" --allow-cache-fallback
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Naver OpenAPI ingest failed; continuing with existing naver/pre_news artifacts."
        }

        if (-not $SkipExaMacroNewsRefresh) {
            Write-Host "==> Run-BtrackExaMacroNewsChain_v1.ps1 (fetch only; reuse staging if no EXA_API_KEY)" -ForegroundColor Cyan
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\Run-BtrackExaMacroNewsChain_v1.ps1" `
                -SkipAdapter -AppendStaging
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Exa macro news refresh failed; continuing with existing staging."
            }
        }

        if (-not $SkipExternalFeedRefresh) {
            Write-Host "==> load_external_feed_drop_with_fallback_v1.py (3rd-leg external drop)" -ForegroundColor Cyan
            & py -3 "scripts\load_external_feed_drop_with_fallback_v1.py" --allow-empty
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "External feed drop validation failed; continuing with existing validated drop."
            }

            Write-Host "==> fetch_external_macro_news_signals_v1.py (FRED macro + NewsAPI if keyed)" -ForegroundColor Cyan
            & py -3 "scripts\fetch_external_macro_news_signals_v1.py" --allow-cache-fallback
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "External macro/news API fetch failed; continuing with feed drop + cache."
            }
        }

        $externalNewsFeedResolved = Join-Path $WorkspaceRoot $ExternalNewsFeedJson
        $lensArgs = @("scripts\build_btrack_news_macro_lens_adapters_v1.py")
        if (Test-Path -LiteralPath $externalNewsFeedResolved) {
            $lensArgs += @("--external-news-feed", $ExternalNewsFeedJson)
        }
        Write-Host "==> build_btrack_news_macro_lens_adapters_v1.py (naver+exa+external drop)" -ForegroundColor Cyan
        & py -3 @lensArgs
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\run_global_atom_pre_news_shadow_chain_v1.ps1" `
        -BatchReportJson $PreNewsBatchReportJson `
        -PreNewsInputJson $PreNewsInputJson
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    if (-not $SkipBiblicalHistoryChronicleRefresh) {
        Write-Host "==> build_chronicle_history_news_signal_stub_v1.py (B-track chronicle daily)" -ForegroundColor Cyan
        & py -3 "scripts\build_chronicle_history_news_signal_stub_v1.py"
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Chronicle signal refresh failed; continuing with existing chronicle history."
        }
        else {
            & py -3 "scripts\evaluate_chronicle_history_news_signal_weekly_v1.py"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Chronicle weekly eval failed; continuing."
            }
            & py -3 "scripts\build_chronicle_pr1_daily_overlay_v1.py"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Chronicle PR1 overlay build failed; continuing."
            }
            & py -3 "scripts\ingest_dss_apocrypha_research_context_v1.py"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "DSS apocrypha research context ingest failed; continuing."
            }
            & py -3 "scripts\build_dss_authority_readiness_reconciliation_v1.py"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "DSS authority readiness reconciliation failed; continuing."
            }
            & py -3 "scripts\ingest_dss_ndjson_token_manifest_research_context_v1.py" `
                --merge-into "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "DSS NDJSON manifest research context ingest failed; continuing."
            }
            & py -3 "scripts\build_chronicle_h_dss1_daily_overlay_v1.py"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Chronicle H-DSS1 overlay build failed; continuing."
            }
            & py -3 "scripts\eval_biblical_history_h_dss1_chronicle_hold_alignment_v1.py"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "H-DSS1 chronicle hold alignment failed; continuing."
            }
            & py -3 "scripts\build_biblical_resonance_research_production_ab_v1.py"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Biblical resonance research/production AB failed; continuing."
            }
            & py -3 "scripts\build_dss_ndjson_resonance_uplift_report_v1.py"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "DSS NDJSON resonance uplift report failed; continuing."
            }
            & py -3 "scripts\evaluate_biblical_resonance_hypotheses_v1.py" `
                --lookback-days 90 `
                --output-json "reports\biblical_resonance_eval_production_90d_latest.json"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Biblical resonance production 90d eval failed; continuing."
            }
        }
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

if (-not $SkipLiveProphecyTriage -and ($OperationModeBShadow -or $EnablePreNewsShadow)) {
    $liveHealthScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\check_live_trading_health.ps1"
    if (Test-Path -LiteralPath $liveHealthScript) {
        Write-Host "==> check_live_trading_health.ps1 (live ops snapshot for triage)" -ForegroundColor Cyan
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $liveHealthScript
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Live trading health check failed; continuing with stale live_trading_health_latest.json if present."
        }
    }
    else {
        Write-Warning "Missing live health script: $liveHealthScript"
    }

    Write-Host "==> build_live_vs_prophecy_triage_v1.py" -ForegroundColor Cyan
    & py -3 "scripts\build_live_vs_prophecy_triage_v1.py"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Host "==> evaluate_prophecy_runtime_health_v1.py (post-live-health refresh)" -ForegroundColor Cyan
    $rhTailArgs = @("scripts\evaluate_prophecy_runtime_health_v1.py")
    if ($OperationModeBShadow) {
        $rhTailArgs += "--operation-mode-b-shadow"
    }
    & py -3 @rhTailArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Host "==> build_live_vs_prophecy_triage_v1.py (final)" -ForegroundColor Cyan
    & py -3 "scripts\build_live_vs_prophecy_triage_v1.py"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

exit 0
