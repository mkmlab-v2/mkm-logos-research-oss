param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipBundle,
    [double]$OverlapDriftAlertThreshold = -0.05,
    [switch]$SkipNightWatchmanHarness,
    [switch]$SkipBtrackGates,
    [switch]$SkipGeneralProphecyChain,
    [switch]$SkipNetSourceFallbackAutoHold,
    [string]$CloseReturnPct = "",
    [string]$PredictedBand = "DOWN_STRONG",
    [string]$HypothesisMetric = "KOSPI_D1_RETURN_PCT",
    [string]$MarketVenue = "KRX",
    [string]$HitThresholdPct = "",
    [string]$FailThresholdPct = "",
    [string]$SecondaryHypothesisMetric = "",
    [string]$SecondaryMarketVenue = "",
    [string]$SecondaryCloseReturnPct = "",
    [string]$SecondaryPredictedBand = "DOWN_STRONG",
    [string]$SecondaryHitThresholdPct = "",
    [string]$SecondaryFailThresholdPct = "",
    [switch]$SkipKospiSasangDynamicsVerify,
    [switch]$SkipBiblicalExternalRealityLockedProfile,
    [switch]$StrictGeneralExplainabilityQualityGate,
    [switch]$AllowLensFallback,
    [switch]$UseWalkForwardBackfilledHistory,
    [string]$WalkForwardBackfillStartDate = "",
    [string]$WalkForwardBackfillEndDate = "",
    [switch]$SkipExternalFeedValidation,
    [switch]$StrictExternalFeedValidation
)

$ErrorActionPreference = "Stop"

if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $workspace = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
} elseif (-not [string]::IsNullOrWhiteSpace([string]$env:MKM_WORKSPACE_ROOT) -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $workspace = (Resolve-Path -LiteralPath $env:MKM_WORKSPACE_ROOT).Path
} else {
    $workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $workspace

$maint = [System.Environment]::GetEnvironmentVariable("MKM_WORKSPACE_MAINTENANCE")
if ($maint -and ($maint.Trim().ToLower() -in @("1", "true", "yes", "on"))) {
    Write-Host "SKIP: MKM_WORKSPACE_MAINTENANCE active (monthly check not run)" -ForegroundColor Yellow
    exit 0
}

$externalFeedValidationMode = "skipped"
if (-not $SkipExternalFeedValidation) {
    $externalLatestRel = "docs\final\artifacts\external_feed_drop_latest.json"
    $externalLatest = Join-Path $workspace $externalLatestRel
    $externalValidatedRel = "docs\final\artifacts\external_feed_drop_latest.validated.json"
    $externalStatusRel = "docs\final\artifacts\external_feed_drop_validation_status_latest.json"
    $externalLoader = Join-Path $workspace "scripts\load_external_feed_drop_with_fallback_v1.py"
    if (Test-Path -LiteralPath $externalLoader) {
        if (Test-Path -LiteralPath $externalLatest) {
            Write-Host "[waiting-queue-check] External feed validate+fallback (B-track research-only)..."
            py $externalLoader --latest $externalLatestRel --output $externalValidatedRel --status-output $externalStatusRel
            if ($LASTEXITCODE -ne 0) {
                if ($StrictExternalFeedValidation) {
                    throw "external feed validation failed (strict mode) exit $LASTEXITCODE"
                }
                Write-Host "[waiting-queue-check] WARN: external feed validation failed; continue in degraded mode (research-only)." -ForegroundColor Yellow
                $externalFeedValidationMode = "degraded"
            } else {
                $externalFeedValidationMode = "latest_or_fallback_ok"
            }
        } else {
            Write-Host "[waiting-queue-check] Skip external feed validate (missing latest drop): $externalLatestRel" -ForegroundColor DarkYellow
            $externalFeedValidationMode = "missing_latest_drop"
        }
    } else {
        Write-Host "[waiting-queue-check] Skip external feed validate (missing loader): scripts\load_external_feed_drop_with_fallback_v1.py" -ForegroundColor DarkYellow
        $externalFeedValidationMode = "missing_loader"
    }
}

$logPath = "$workspace\docs\final\artifacts\waiting_queue_monthly_check_log.jsonl"
$sourceHuntSummaryPath = "$workspace\docs\final\artifacts\entry16_source_hunt_summary.json"
$promotionGatePath = "$workspace\docs\final\artifacts\entry16_promotion_gate.json"
$decisionLockPath = "$workspace\docs\final\artifacts\entry16_manual_promotion_decision_lock_latest.json"
$highReliabilityGatePath = "$workspace\docs\final\artifacts\high_reliability_mode_gate_latest.json"
$monthlyProphecyPath = "$workspace\docs\final\artifacts\prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
$biblicalExternalDualgateStabilityPath = "$workspace\docs\final\artifacts\biblical_external_dualgate_stability_v1_latest.json"
$biblicalExternalRealityStatus = "skipped"
$biblicalFixedCommercialOpsRelaxed = $null
$runtimeRiskProfilePath = "$workspace\projects\bitcoin-trading\memory\v2\risk\risk_profile_fact_safe_latest.json"
$riskProfileSourceName = [string]$env:RISK_PROFILE_SOURCE_NAME
$riskProfileModeName = [string]$env:RISK_PROFILE_MODE_NAME
# Preserve source/mode from existing runtime profile when env overrides are absent (n8n metadata guard).
if (([string]::IsNullOrWhiteSpace($riskProfileSourceName) -or [string]::IsNullOrWhiteSpace($riskProfileModeName)) -and (Test-Path -LiteralPath $runtimeRiskProfilePath)) {
    try {
        $existingProfile = Get-Content -LiteralPath $runtimeRiskProfilePath -Raw -Encoding utf8 | ConvertFrom-Json
        if ([string]::IsNullOrWhiteSpace($riskProfileSourceName) -and -not [string]::IsNullOrWhiteSpace([string]$existingProfile.source)) {
            $riskProfileSourceName = [string]$existingProfile.source
        }
        if ([string]::IsNullOrWhiteSpace($riskProfileModeName) -and -not [string]::IsNullOrWhiteSpace([string]$existingProfile.mode)) {
            $riskProfileModeName = [string]$existingProfile.mode
        }
    } catch {
    }
}
$symbolLaneProfileComparePath = "$workspace\reports\constitution\btrack_pilot\symbol_lane_profile_compare_latest.json"
$btrackGatePath = "$workspace\reports\constitution\btrack_pilot\btrack_promotion_gate_anchor_verified_only_latest.json"
$symbolLaneGatePath = "$workspace\reports\constitution\btrack_pilot\symbol_lane_gate_latest.json"
$slackDeliveryStatusPath = "$workspace\reports\constitution\btrack_pilot\fact_safe_slack_delivery_latest.json"
$slackDeliveryLogPath = "$workspace\reports\constitution\btrack_pilot\fact_safe_slack_delivery_log.jsonl"
$costWatchMonitorPath = "$workspace\docs\final\artifacts\cost_watch_monitor_latest.json"
$regimeSwitchReportPath = "$workspace\docs\final\artifacts\btc_time_machine_regime_switch_backtest_latest.json"
$billingEvidencePath = "$workspace\docs\final\artifacts\billing_evidence_latest.json"
$hallucinationEvalPath = "$workspace\docs\final\artifacts\hallucination_grounding_eval_latest.json"
$weeklyReliabilitySnapshotPath = "$workspace\docs\final\artifacts\trinity_weekly_reliability_snapshot_latest.json"
$scoringDistributionPath = "$workspace\docs\final\artifacts\trinity_scoring_distribution_latest.json"
$fusedCalibrationScriptPath = "$workspace\scripts\report_fused_paper_cycle_calibration_30.py"
$expandedDatasetPath = "$workspace\reports\constitution\btrack_pilot\vllm_ab_dataset_expanded_latest.jsonl"
$highSampleRepeatPath = "$workspace\reports\constitution\btrack_pilot\vllm_ab_canary_repeat_high_sample_latest.json"
$expandedDatasetScriptPath = "$workspace\scripts\generate_vllm_ab_dataset_expanded.py"
$highSampleRepeatScriptPath = "$workspace\scripts\run_vllm_ab_canary_repeat.py"
$billingInvoiceFromEnvPath = "$workspace\docs\final\artifacts\billing_invoice_from_env_latest.json"
$billingInvoiceFromEnvScriptPath = "$workspace\scripts\emit_billing_invoice_from_env.py"
$billingEvidenceScriptPath = "$workspace\scripts\report_billing_evidence_from_vllm.py"
$hallucinationEvalScriptPath = "$workspace\scripts\report_hallucination_grounding_eval.py"
$costWatchScriptPath = "$workspace\scripts\report_cost_watch_monitor.py"
$regimeSwitchScriptPath = "$workspace\scripts\run_btc_time_machine_regime_switch_backtest.py"
$lensMyeongniScriptPath = "$workspace\scripts\run_lens_myeongni.py"
$lensSasangScriptPath = "$workspace\scripts\run_lens_sasang.py"
$lensLogosScriptPath = "$workspace\scripts\run_lens_logos.py"
$lensFusionStubScriptPath = "$workspace\scripts\report_independent_lens_fusion_stub_v0.py"
$lensShadowGateScriptPath = "$workspace\scripts\report_independent_lens_shadow_gate.py"
$lensShadowMinorityMonthlyScriptPath = "$workspace\scripts\report_independent_lens_shadow_minority_monthly_v1.py"
$insightScoreboardScriptPath = "$workspace\scripts\build_insight_effectiveness_scoreboard.py"
$c2GuardrailScriptPath = "$workspace\scripts\check_c2_aegis_guardrail.py"
$c2GuardrailPath = "$workspace\docs\final\artifacts\C2_AEGIS_BASELINE_GUARDRAIL_V1.json"
$c2CurrentScoreboardPath = "$workspace\docs\final\artifacts\aegis_unified_scoreboard_btc90_k010_latest.json"
$c2GuardrailStatusPath = "$workspace\docs\final\artifacts\c2_aegis_guardrail_status_latest.json"
$reportSchemaV2FromChainScriptPath = "$workspace\scripts\experimental\codebook_runtime_pack\build_report_schema_v2_from_chain_artifacts.py"
$reportSchemaV2LabelKpiScriptPath = "$workspace\scripts\experimental\codebook_runtime_pack\build_report_schema_v2_label_kpi.py"
$reportSchemaV2QualityAlertScriptPath = "$workspace\scripts\experimental\codebook_runtime_pack\build_report_schema_v2_quality_alert.py"
$dailySitrepPath = "$workspace\docs\final\artifacts\waiting_queue_daily_sitrep_latest.txt"
$generalExplainabilityQualityPath = "$workspace\docs\final\artifacts\general_prophecy_explainability_quality_v1_latest.json"
$btrackRecommendationPackPath = "$workspace\reports\notebooklm\btrack_insight_recommendation_pack_latest.json"
$btrackMonthlyBriefBuilderPath = "$workspace\scripts\build_btrack_monthly_brief_from_recommendation.py"
$walkForwardEvalScriptPath = "$workspace\scripts\eval_btrack_walk_forward_hit_rate_v1.py"
$evalComparisonScriptPath = "$workspace\scripts\build_prophecy_eval_comparison_report_v1.py"
$walkForwardHistoryBuilderScriptPath = "$workspace\scripts\build_fusion_shadow_daily_history_v1.py"
$walkForwardRawHistoryPath = "$workspace\docs\final\artifacts\independent_lens_fusion_shadow_history.jsonl"
$walkForwardBackfilledHistoryPath = "$workspace\docs\final\artifacts\independent_lens_fusion_shadow_daily_backfilled_latest.jsonl"
$walkForwardEvalLatestPath = "$workspace\docs\final\artifacts\prophecy_hit_rate_eval_walk_forward_30d_2026-04-17.json"
$evalComparisonLatestPath = "$workspace\docs\final\artifacts\prophecy_eval_comparison_report_latest.json"
$walkForwardSyntheticRatioWarnThreshold = 0.30
if ($env:WALK_FORWARD_SYNTHETIC_RATIO_WARN_THRESHOLD) {
    try {
        $walkForwardSyntheticRatioWarnThreshold = [double]$env:WALK_FORWARD_SYNTHETIC_RATIO_WARN_THRESHOLD
    } catch {
        $walkForwardSyntheticRatioWarnThreshold = 0.30
    }
}
$softFailNotes = New-Object System.Collections.Generic.List[string]
$allowLensFallbackState = if ($AllowLensFallback) { "enabled" } else { "disabled" }

function Add-SoftFailNote([string]$message) {
    $softFailNotes.Add($message) | Out-Null
    Write-Host "[waiting-queue-check][WARN] $message"
}
$latestKpiPath = "$workspace\projects\bitcoin-trading\memory\kpi\latest_kpi.json"
$inputUsdPer1k = 0.0
$outputUsdPer1k = 0.0
if ($env:FACT_SAFE_INPUT_USD_PER_1K_TOKENS) {
    $inputUsdPer1k = [double]$env:FACT_SAFE_INPUT_USD_PER_1K_TOKENS
}
if ($env:FACT_SAFE_OUTPUT_USD_PER_1K_TOKENS) {
    $outputUsdPer1k = [double]$env:FACT_SAFE_OUTPUT_USD_PER_1K_TOKENS
}
$enableHighSampleVllmEval = $false
if ($env:FACT_SAFE_ENABLE_HIGH_SAMPLE_VLLM_EVAL) {
    $enableHighSampleVllmEval = ([string]$env:FACT_SAFE_ENABLE_HIGH_SAMPLE_VLLM_EVAL).ToLower() -in @("1", "true", "yes")
}
$highSampleCases = 100
if ($env:FACT_SAFE_HIGH_SAMPLE_CASES) {
    $highSampleCases = [int]$env:FACT_SAFE_HIGH_SAMPLE_CASES
}
$highSampleRuns = 10
if ($env:FACT_SAFE_HIGH_SAMPLE_RUNS) {
    $highSampleRuns = [int]$env:FACT_SAFE_HIGH_SAMPLE_RUNS
}
$skipNetSourceFallbackAutoHoldEffective = $SkipNetSourceFallbackAutoHold
if ($env:FACT_SAFE_SKIP_NET_SOURCE_FALLBACK_AUTO_HOLD) {
    $skipNetSourceFallbackAutoHoldEffective = ([string]$env:FACT_SAFE_SKIP_NET_SOURCE_FALLBACK_AUTO_HOLD).ToLower() -in @("1", "true", "yes")
}
$skipBiblicalExternalRealityEffective = $SkipBiblicalExternalRealityLockedProfile
if ($env:FACT_SAFE_SKIP_BIBLICAL_EXTERNAL_REALITY_LOCKED) {
    $skipBiblicalExternalRealityEffective = ([string]$env:FACT_SAFE_SKIP_BIBLICAL_EXTERNAL_REALITY_LOCKED).ToLower() -in @("1", "true", "yes")
}
$generalExplainabilityCoverageMin = 1.0
if ($env:GENERAL_EXPLAINABILITY_COVERAGE_MIN) {
    $generalExplainabilityCoverageMin = [double]$env:GENERAL_EXPLAINABILITY_COVERAGE_MIN
}
$generalExplainabilityConflictMin = 1.0
if ($env:GENERAL_EXPLAINABILITY_CONFLICT_MIN) {
    $generalExplainabilityConflictMin = [double]$env:GENERAL_EXPLAINABILITY_CONFLICT_MIN
}
$generalExplainabilityReproMin = 0.30
if ($env:GENERAL_EXPLAINABILITY_REPRO_MIN) {
    $generalExplainabilityReproMin = [double]$env:GENERAL_EXPLAINABILITY_REPRO_MIN
}
$generalExplainabilityQualityGate = "skipped"
$generalExplainabilityQualityReason = $null
$generalExplainabilityCoverageRate = $null
$generalExplainabilityConflictRate = $null
$generalExplainabilityReproRate = $null
$checkedAtObj = [DateTimeOffset]::UtcNow
$checkedAt = $checkedAtObj.ToString("o")
$nextMonthlyDue = $checkedAtObj.AddDays(30).ToString("yyyy-MM-dd")
$horizonT30 = $checkedAtObj.AddDays(30).ToString("yyyy-MM-dd")
$horizonT90 = $checkedAtObj.AddDays(90).ToString("yyyy-MM-dd")
$bundleMode = if ($SkipBundle) { "skip_bundle" } else { "full_bundle" }

Write-Host "[waiting-queue-check] Running CROSS_REF schema gates..."
py -m pytest tests/test_cross_ref_dss_schema.py -q --tb=short
if ($LASTEXITCODE -ne 0) {
    throw "CROSS_REF schema gates failed with exit code $LASTEXITCODE"
}

if (-not $SkipBundle) {
    Write-Host "[waiting-queue-check] Running full prophecy alignment bundle..."
    & "$workspace\projects\bitcoin-trading\ops\v2\tasks\run_prophecy_alignment_pytest.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "Prophecy alignment bundle failed with exit code $LASTEXITCODE"
    }
}

Write-Host "[waiting-queue-check] Generating ENTRY_16 source-hunt summary..."
py scripts/report_entry16_source_hunt.py
if ($LASTEXITCODE -ne 0) {
    throw "ENTRY_16 source-hunt summary failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Evaluating ENTRY_16 promotion gate..."
py scripts/evaluate_entry16_promotion_gate.py
if ($LASTEXITCODE -ne 0) {
    throw "ENTRY_16 promotion gate evaluation failed with exit code $LASTEXITCODE"
}

$btrackVerifiedGateStatus = "pass"
$btrackSymbolLaneGateStatus = "pass"
if ($SkipBtrackGates) {
    $btrackVerifiedGateStatus = "skipped"
    $btrackSymbolLaneGateStatus = "skipped"
    Write-Host "[waiting-queue-check] Skipping B-Track gate workflows by flag."
} else {
    Write-Host "[waiting-queue-check] Running B-Track verified gate+lock..."
    & "$workspace\scripts\run_btrack_gate_and_lock.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "B-Track verified gate+lock failed with exit code $LASTEXITCODE"
    }

    Write-Host "[waiting-queue-check] Running B-Track symbol lane gate..."
    py scripts/run_btrack_symbol_lane_gate_and_lock.py
    if ($LASTEXITCODE -ne 0) {
        throw "B-Track symbol lane gate+lock failed with exit code $LASTEXITCODE"
    }

    Write-Host "[waiting-queue-check] Building symbol lane profile compare..."
    py scripts/report_symbol_lane_profile_compare.py
    if ($LASTEXITCODE -ne 0) {
        throw "Symbol lane profile compare failed with exit code $LASTEXITCODE"
    }
}

$topOverlapRate = $null
if (Test-Path -LiteralPath $symbolLaneProfileComparePath) {
    try {
        $slObj = Get-Content -LiteralPath $symbolLaneProfileComparePath -Encoding utf8 | ConvertFrom-Json
        $topOverlapRate = $slObj.c_queue_delta.top_overlap_rate
    } catch {
        $topOverlapRate = $null
    }
}

$deltaVsPrevOverlap = $null
if (Test-Path -LiteralPath $logPath) {
    try {
        $prevLines = Get-Content -LiteralPath $logPath -Encoding utf8
        if ($prevLines.Count -gt 0) {
            $prevObj = ($prevLines[-1] | ConvertFrom-Json)
            $prevTop = $prevObj.top_overlap_rate
            if (($null -ne $topOverlapRate) -and ($null -ne $prevTop)) {
                $deltaVsPrevOverlap = [double]$topOverlapRate - [double]$prevTop
            }
        }
    } catch {
        $deltaVsPrevOverlap = $null
    }
}

$overlapDriftAlert = $false
if ($null -ne $deltaVsPrevOverlap) {
    $overlapDriftAlert = ([double]$deltaVsPrevOverlap -le [double]$OverlapDriftAlertThreshold)
}

Write-Host "[waiting-queue-check] Evaluating high-reliability mode gate..."
py scripts/report_high_reliability_mode_gate.py
if ($LASTEXITCODE -ne 0) {
    throw "High-reliability mode gate failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Running BTC time-machine backtest (fact-safe evidence)..."
py scripts/run_btc_time_machine_fact_safe_backtest.py --start 2025-01-01 --end 2025-12-31
if ($LASTEXITCODE -ne 0) {
    throw "BTC time-machine fact-safe backtest failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Running BTC time-machine sweep (evidence scaling, 2025-2026 only for speed)..."
py scripts/run_btc_time_machine_backtest_sweep.py --periods "2025-01-01:2025-12-31,2026-01-01:2026-12-31"
if ($LASTEXITCODE -ne 0) {
    throw "BTC time-machine sweep failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Generating 2026 monthly KOSPI/BTC prophecy (fact-safe)..."
py scripts/generate_2026_monthly_kospi_btc_prophecy.py
if ($LASTEXITCODE -ne 0) {
    throw "2026 monthly KOSPI/BTC prophecy generation failed with exit code $LASTEXITCODE"
}

if (-not $skipBiblicalExternalRealityEffective) {
    Write-Host "[waiting-queue-check] Biblical external reality locked profile + dual-gate stability (staged-search defaults when present)..."
    $biblicalProfileScript = "$workspace\scripts\Run-BiblicalExternalRealityLockedProfile.ps1"
    $biblicalGateScript = "$workspace\scripts\check_biblical_external_reality_gate_v1.py"
    if ((Test-Path -LiteralPath $biblicalProfileScript) -and (Test-Path -LiteralPath $biblicalGateScript)) {
        & $biblicalProfileScript -UseStagedSearchDefaults
        if ($LASTEXITCODE -ne 0) {
            Add-SoftFailNote "Run-BiblicalExternalRealityLockedProfile.ps1 failed with exit code $LASTEXITCODE; marked soft-fail"
            $biblicalExternalRealityStatus = "soft_fail"
        } else {
            $biblicalExternalRealityStatus = "pass"
        }
    } else {
        Add-SoftFailNote "Biblical external reality profile dependencies missing; skipped"
        $biblicalExternalRealityStatus = "missing_dependency"
    }
    if (Test-Path -LiteralPath $biblicalExternalDualgateStabilityPath) {
        try {
            $stabDoc = Get-Content -LiteralPath $biblicalExternalDualgateStabilityPath -Raw -Encoding utf8 | ConvertFrom-Json
            if ($null -ne $stabDoc.aggregate.fixed_commercial_ops_relaxed) {
                $biblicalFixedCommercialOpsRelaxed = [bool]$stabDoc.aggregate.fixed_commercial_ops_relaxed
            }
        } catch {
            $biblicalFixedCommercialOpsRelaxed = $null
        }
    }
} else {
    Write-Host "[waiting-queue-check] Skipping biblical external reality locked profile (flag or FACT_SAFE_SKIP_BIBLICAL_EXTERNAL_REALITY_LOCKED)."
}

if (-not $SkipGeneralProphecyChain) {
    Write-Host "[waiting-queue-check] General prophecy B-rail chain (registry validate, brief, Brier eval, LoRA JSONL export; no external APIs)..."
    py scripts/generate_general_prophecy_v1.py
    if ($LASTEXITCODE -ne 0) {
        throw "generate_general_prophecy_v1 failed with exit code $LASTEXITCODE"
    }
    py scripts/build_general_prophecy_explainable_v1.py
    if ($LASTEXITCODE -ne 0) {
        throw "build_general_prophecy_explainable_v1 failed with exit code $LASTEXITCODE"
    }
    py scripts/report_general_prophecy_explainability_quality_v1.py
    if ($LASTEXITCODE -ne 0) {
        throw "report_general_prophecy_explainability_quality_v1 failed with exit code $LASTEXITCODE"
    }
    if (Test-Path -LiteralPath $generalExplainabilityQualityPath) {
        try {
            $gqObj = Get-Content -LiteralPath $generalExplainabilityQualityPath -Raw -Encoding utf8 | ConvertFrom-Json
            $generalExplainabilityCoverageRate = $gqObj.summary.coverage_rate
            $generalExplainabilityConflictRate = $gqObj.summary.conflict_resolution_rate
            $generalExplainabilityReproRate = $gqObj.summary.reproducible_evidence_rate
            $gateCoverageOk = ($null -ne $generalExplainabilityCoverageRate) -and ([double]$generalExplainabilityCoverageRate -ge [double]$generalExplainabilityCoverageMin)
            $gateConflictOk = ($null -ne $generalExplainabilityConflictRate) -and ([double]$generalExplainabilityConflictRate -ge [double]$generalExplainabilityConflictMin)
            $gateReproOk = ($null -ne $generalExplainabilityReproRate) -and ([double]$generalExplainabilityReproRate -ge [double]$generalExplainabilityReproMin)
            if ($gateCoverageOk -and $gateConflictOk -and $gateReproOk) {
                $generalExplainabilityQualityGate = "pass"
                $generalExplainabilityQualityReason = "all_thresholds_satisfied"
            } else {
                $generalExplainabilityQualityGate = "fail"
                $generalExplainabilityQualityReason = "threshold_below_min"
                $gateMsg = "general explainability quality gate fail: coverage=$generalExplainabilityCoverageRate (min=$generalExplainabilityCoverageMin), conflict=$generalExplainabilityConflictRate (min=$generalExplainabilityConflictMin), reproducible=$generalExplainabilityReproRate (min=$generalExplainabilityReproMin)"
                if ($StrictGeneralExplainabilityQualityGate) {
                    throw $gateMsg
                }
                Add-SoftFailNote $gateMsg
            }
        } catch {
            $generalExplainabilityQualityGate = "parse_error"
            $generalExplainabilityQualityReason = "quality_report_parse_error"
            if ($StrictGeneralExplainabilityQualityGate) {
                throw "general explainability quality parse failed"
            }
            Add-SoftFailNote "general explainability quality parse failed; gate marked parse_error"
        }
    } else {
        $generalExplainabilityQualityGate = "missing"
        $generalExplainabilityQualityReason = "quality_report_missing"
        if ($StrictGeneralExplainabilityQualityGate) {
            throw "general explainability quality report missing: $generalExplainabilityQualityPath"
        }
        Add-SoftFailNote "general explainability quality report missing; gate marked missing"
    }
    py scripts/sync_biblical_lane_hook_to_bitcoin_trading.py
    if ($LASTEXITCODE -ne 0) {
        throw "sync_biblical_lane_hook_to_bitcoin_trading failed with exit code $LASTEXITCODE"
    }
    py scripts/build_general_prophecy_brief.py
    if ($LASTEXITCODE -ne 0) {
        throw "build_general_prophecy_brief failed with exit code $LASTEXITCODE"
    }
    py scripts/eval_general_prophecy_brier_score.py
    if ($LASTEXITCODE -ne 0) {
        throw "eval_general_prophecy_brier_score failed with exit code $LASTEXITCODE"
    }
    py scripts/export_general_prophecy_to_jsonl.py
    if ($LASTEXITCODE -ne 0) {
        throw "export_general_prophecy_to_jsonl failed with exit code $LASTEXITCODE"
    }
    if (Test-Path -LiteralPath "$workspace\scripts\verify_general_prophecy_monthly_artifacts_v1.py") {
        Write-Host "[waiting-queue-check] Verifying monthly artifact triage (brief/brier/shortlist)..."
        py scripts/verify_general_prophecy_monthly_artifacts_v1.py
        if ($LASTEXITCODE -ne 0) {
            throw "verify_general_prophecy_monthly_artifacts_v1 failed with exit code $LASTEXITCODE"
        }
    }
    if ((Test-Path -LiteralPath "$workspace\scripts\build_mkm_episode_refinery_v1.py") -and (Test-Path -LiteralPath "$workspace\scripts\validate_mkm_episode_refinery_v1.py")) {
        Write-Host "[waiting-queue-check] Building MKM Episode v1 refinery artifacts..."
        py scripts/build_mkm_episode_refinery_v1.py
        if ($LASTEXITCODE -ne 0) {
            throw "build_mkm_episode_refinery_v1 failed with exit code $LASTEXITCODE"
        }
        Write-Host "[waiting-queue-check] Validating MKM Episode v1 refinery artifacts..."
        py scripts/validate_mkm_episode_refinery_v1.py
        if ($LASTEXITCODE -ne 0) {
            throw "validate_mkm_episode_refinery_v1 failed with exit code $LASTEXITCODE"
        }
    }
    if (Test-Path -LiteralPath "$workspace\scripts\mkm_policy_gradient_optimizer.py") {
        Write-Host "[waiting-queue-check] Running MKM policy gradient optimizer..."
        py scripts/mkm_policy_gradient_optimizer.py
        if ($LASTEXITCODE -ne 0) {
            throw "mkm_policy_gradient_optimizer failed with exit code $LASTEXITCODE"
        }
    }
    if (Test-Path -LiteralPath "$workspace\scripts\build_human_insight_attribution_v1.py") {
        Write-Host "[waiting-queue-check] Building human insight attribution weights..."
        py scripts/build_human_insight_attribution_v1.py
        if ($LASTEXITCODE -ne 0) {
            throw "build_human_insight_attribution_v1 failed with exit code $LASTEXITCODE"
        }
    }
    if (Test-Path -LiteralPath "$workspace\scripts\promote_mkm_policy_from_optimizer_v1.py") {
        Write-Host "[waiting-queue-check] Evaluating MKM policy promotion gate..."
        py scripts/promote_mkm_policy_from_optimizer_v1.py
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[waiting-queue-check] MKM policy promotion applied."
        } else {
            Write-Host "[waiting-queue-check] MKM policy promotion held (guardrails or decisions not met)." -ForegroundColor DarkYellow
        }
    }

    Write-Host "[waiting-queue-check] Multiline prophecy delegated bundle (live + shadow bootstrap)..."
    if (Test-Path -LiteralPath "$workspace\scripts\run_multiline_prophecy_delegated_bundle_v0.py") {
        py scripts/run_multiline_prophecy_delegated_bundle_v0.py
        if ($LASTEXITCODE -ne 0) {
            throw "run_multiline_prophecy_delegated_bundle_v0 failed with exit code $LASTEXITCODE"
        }
        if (Test-Path -LiteralPath "$workspace\scripts\run_multiline_prophecy_policy_gate_v0.py") {
            py scripts/run_multiline_prophecy_policy_gate_v0.py
            if ($LASTEXITCODE -ne 0) {
                throw "run_multiline_prophecy_policy_gate_v0 failed with exit code $LASTEXITCODE"
            }
            if (Test-Path -LiteralPath "$workspace\scripts\report_multiline_prophecy_weight_monitor_v0.py") {
                py scripts/report_multiline_prophecy_weight_monitor_v0.py
                if ($LASTEXITCODE -ne 0) {
                    throw "report_multiline_prophecy_weight_monitor_v0 failed with exit code $LASTEXITCODE"
                }
            } else {
                Add-SoftFailNote "report_multiline_prophecy_weight_monitor_v0.py missing; skipped"
            }
            if (Test-Path -LiteralPath "$workspace\scripts\run_multiline_prophecy_utility_validation_v1.py") {
                py scripts/run_multiline_prophecy_utility_validation_v1.py
                if ($LASTEXITCODE -ne 0) {
                    throw "run_multiline_prophecy_utility_validation_v1 failed with exit code $LASTEXITCODE"
                }
            } else {
                Add-SoftFailNote "run_multiline_prophecy_utility_validation_v1.py missing; skipped"
            }
            if (Test-Path -LiteralPath "$workspace\scripts\run_multiline_prophecy_model_selection_v1.py") {
                py scripts/run_multiline_prophecy_model_selection_v1.py
                if ($LASTEXITCODE -ne 0) {
                    throw "run_multiline_prophecy_model_selection_v1 failed with exit code $LASTEXITCODE"
                }
            } else {
                Add-SoftFailNote "run_multiline_prophecy_model_selection_v1.py missing; skipped"
            }
            if (Test-Path -LiteralPath "$workspace\scripts\run_manseryeok_caller_preprocess_crosssuite_v2.py") {
                py scripts/run_manseryeok_caller_preprocess_crosssuite_v2.py
                if ($LASTEXITCODE -ne 0) {
                    throw "run_manseryeok_caller_preprocess_crosssuite_v2 failed with exit code $LASTEXITCODE"
                }
            } else {
                Add-SoftFailNote "run_manseryeok_caller_preprocess_crosssuite_v2.py missing; skipped"
            }
            if (Test-Path -LiteralPath "$workspace\scripts\run_manseryeok_integrity_gate_v1.py") {
                if (Test-Path -LiteralPath "$workspace\scripts\run_manseryeok_boundary_alignment_policy_check_v1.py") {
                    py scripts/run_manseryeok_boundary_alignment_policy_check_v1.py
                    if ($LASTEXITCODE -ne 0) {
                        throw "run_manseryeok_boundary_alignment_policy_check_v1 failed with exit code $LASTEXITCODE"
                    }
                    if (Test-Path -LiteralPath "$workspace\tests\fixtures\manseryeok_calculation_profile_v1.zi23.json") {
                        py scripts/run_manseryeok_boundary_alignment_policy_check_v1.py --profile tests/fixtures/manseryeok_calculation_profile_v1.zi23.json --out docs/final/artifacts/manseryeok_boundary_alignment_policy_check_v1_zi23_latest.json
                        if ($LASTEXITCODE -ne 0) {
                            throw "run_manseryeok_boundary_alignment_policy_check_v1 (zi23) failed with exit code $LASTEXITCODE"
                        }
                        if (Test-Path -LiteralPath "$workspace\scripts\run_manseryeok_zi23_readiness_gate_v1.py") {
                            py scripts/run_manseryeok_zi23_readiness_gate_v1.py
                            if ($LASTEXITCODE -ne 0) {
                                throw "run_manseryeok_zi23_readiness_gate_v1 failed with exit code $LASTEXITCODE"
                            }
                        } else {
                            Add-SoftFailNote "run_manseryeok_zi23_readiness_gate_v1.py missing; zi_23 readiness gate skipped"
                        }
                    } else {
                        Add-SoftFailNote "manseryeok_calculation_profile_v1.zi23.json missing; zi_23 policy check skipped"
                    }
                } else {
                    Add-SoftFailNote "run_manseryeok_boundary_alignment_policy_check_v1.py missing; skipped"
                }
                py scripts/run_manseryeok_integrity_gate_v1.py
                if ($LASTEXITCODE -ne 0) {
                    throw "run_manseryeok_integrity_gate_v1 failed with exit code $LASTEXITCODE"
                }
            } else {
                Add-SoftFailNote "run_manseryeok_integrity_gate_v1.py missing; skipped"
            }
        } else {
            Add-SoftFailNote "run_multiline_prophecy_policy_gate_v0.py missing; skipped"
        }
    } else {
        Add-SoftFailNote "run_multiline_prophecy_delegated_bundle_v0.py missing; skipped"
    }
}

$kospiCsv = Join-Path $workspace "research\market_data\kospi_daily_external_yf.csv"
$hypoJson = Join-Path $workspace "docs\final\artifacts\btrack_hypothesis_prophecy_latest.json"
$scoreJson = Join-Path $workspace "docs\final\artifacts\btrack_prophecy_score_latest.json"
if ((Test-Path -LiteralPath $kospiCsv) -and (Test-Path -LiteralPath $hypoJson)) {
    Write-Host "[waiting-queue-check] B-Track OHLCV score + prophecy hit-rate eval (price mode, last 30 trading days)..."
    $buildBtrackArgs = @("scripts/build_btrack_prophecy_score_from_ohlcv.py", "--recent-trading-days", "30")
    $btcCsvResolved = $null
    if (-not [string]::IsNullOrWhiteSpace([string]$env:MKM_BTC_DAILY_CSV) -and (Test-Path -LiteralPath $env:MKM_BTC_DAILY_CSV)) {
        $btcCsvResolved = $env:MKM_BTC_DAILY_CSV
    } else {
        $btcCsvDefault = Join-Path $workspace "research\market_data\btc_daily_external_yf.csv"
        if (Test-Path -LiteralPath $btcCsvDefault) {
            $btcCsvResolved = $btcCsvDefault
        }
    }
    if ($btcCsvResolved) {
        $buildBtrackArgs += @("--btc-csv", $btcCsvResolved)
        # Align with burst/Invoke-MaxProphecyBurst: dual-leg rows per eval_date when both OHLCV legs exist (instrument-combo walkforward input).
        $buildBtrackArgs += "--force-dual-leg-panel"
    }
    py @buildBtrackArgs
    if ($LASTEXITCODE -ne 0) {
        throw "build_btrack_prophecy_score_from_ohlcv failed with exit code $LASTEXITCODE"
    }
    if (-not (Test-Path -LiteralPath $scoreJson)) {
        throw "btrack_prophecy_score_latest.json missing after build_btrack_prophecy_score_from_ohlcv"
    }
    $scoreArchive = Join-Path $workspace ("docs\final\artifacts\btrack_prophecy_score_monthly_{0:yyyy-MM-dd}.json" -f (Get-Date))
    Copy-Item -LiteralPath $scoreJson -Destination $scoreArchive -Force
    Write-Host "[waiting-queue-check] Archived btrack score to $scoreArchive"
    $hitEvalJson = Join-Path $workspace "docs\final\artifacts\prophecy_hit_rate_eval_latest.json"
    py scripts/eval_prophecy_hit_rate_v1.py --run-mode price --score-json $scoreJson
    if ($LASTEXITCODE -ne 0) {
        throw "eval_prophecy_hit_rate_v1 (price) failed with exit code $LASTEXITCODE"
    }
    if (Test-Path -LiteralPath $hitEvalJson) {
        $hitArchive = Join-Path $workspace ("docs\final\artifacts\prophecy_hit_rate_eval_monthly_{0:yyyy-MM-dd}.json" -f (Get-Date))
        Copy-Item -LiteralPath $hitEvalJson -Destination $hitArchive -Force
        Write-Host "[waiting-queue-check] Archived hit-rate eval to $hitArchive"
    }
} else {
    Write-Host "[waiting-queue-check] WARN: skipping B-Track hit-rate chain (need kospi CSV + hypothesis JSON)." -ForegroundColor Yellow
}

if (-not $SkipKospiSasangDynamicsVerify) {
    $kospiSasangVerifyPy = Join-Path $workspace "scripts\verify_kospi_sasang_dynamics_holdout_v1.py"
    if ((Test-Path -LiteralPath $kospiCsv) -and (Test-Path -LiteralPath $kospiSasangVerifyPy)) {
        Write-Host "[waiting-queue-check] KOSPI sasang dynamics holdout verify (fast, observational)..."
        py scripts/verify_kospi_sasang_dynamics_holdout_v1.py --fast --mode holdout
        if ($LASTEXITCODE -ne 0) {
            throw "verify_kospi_sasang_dynamics_holdout_v1.py failed with exit code $LASTEXITCODE"
        }
    } else {
        Write-Host "[waiting-queue-check] WARN: skipping KOSPI sasang dynamics verify (need kospi CSV + verify script)." -ForegroundColor Yellow
    }
} else {
    Write-Host "[waiting-queue-check] SkipKospiSasangDynamicsVerify: sasang dynamics verify omitted." -ForegroundColor DarkGray
}

Write-Host "[waiting-queue-check] Syncing trinity risk governor to runtime risk_profile..."
$syncArgs = @("scripts/sync_fact_safe_risk_profile.py", "--prophecy", $monthlyProphecyPath, "--output", $runtimeRiskProfilePath)
if (-not [string]::IsNullOrWhiteSpace($riskProfileSourceName)) {
    $syncArgs += @("--source", $riskProfileSourceName)
}
if (-not [string]::IsNullOrWhiteSpace($riskProfileModeName)) {
    $syncArgs += @("--mode", $riskProfileModeName)
}
py @syncArgs
if ($LASTEXITCODE -ne 0) {
    throw "Fact-Safe risk profile sync failed with exit code $LASTEXITCODE"
}

$priceOutputLockGuard = "pass"
$priceOutputLockReason = $null
$priceOutputLocked = $null
$prophecyReliabilityBadge = $null
$prophecyDecision = $null
$prophecyCoreDecision = $null
$prophecyCoreScore = $null
$prophecyKShieldCandidate = $null
$prophecyKShieldMdd = $null
$prophecyScoringRule = $null
$kShieldMetadataGuard = "pass"
$kShieldMetadataReason = $null
if (Test-Path -LiteralPath $monthlyProphecyPath) {
    try {
        $prophecyObj = Get-Content -LiteralPath $monthlyProphecyPath -Encoding utf8 | ConvertFrom-Json
        $priceOutputLocked = [bool]$prophecyObj.meta.price_output_locked
        $priceOutputLockReason = [string]$prophecyObj.meta.lock_reason
        $prophecyReliabilityBadge = ([string]$prophecyObj.meta.reliability_badge).ToUpper()
        $prophecyDecision = ([string]$prophecyObj.meta.high_reliability_decision).ToUpper()
        $prophecyCoreDecision = ([string]$prophecyObj.meta.core_decision).ToUpper()
        $prophecyCoreScore = $prophecyObj.meta.core_score
        $prophecyKShieldCandidate = [string]$prophecyObj.meta.k_shield_candidate_name
        $prophecyKShieldMdd = $prophecyObj.meta.k_shield_candidate_max_drawdown_pct
        $prophecyScoringRule = $prophecyObj.meta.scoring_rule
        $requiresLock = ($prophecyReliabilityBadge -eq "LOW" -or $prophecyDecision -eq "HOLD")
        if ($requiresLock -and (-not $priceOutputLocked)) {
            $priceOutputLockGuard = "fail"
            if ([string]::IsNullOrWhiteSpace($priceOutputLockReason)) {
                $priceOutputLockReason = "price_output_locked_false"
            }
        }
        if ([string]::IsNullOrWhiteSpace($prophecyCoreDecision)) {
            $priceOutputLockGuard = "fail"
            $priceOutputLockReason = "missing_core_decision"
        }
        if ([string]::IsNullOrWhiteSpace($prophecyKShieldCandidate)) {
            $kShieldMetadataGuard = "fail"
            $kShieldMetadataReason = "missing_k_shield_candidate"
        }
        if ($null -eq $prophecyKShieldMdd) {
            $kShieldMetadataGuard = "fail"
            if ([string]::IsNullOrWhiteSpace($kShieldMetadataReason)) {
                $kShieldMetadataReason = "missing_k_shield_candidate_max_drawdown_pct"
            }
        }
    } catch {
        $priceOutputLockGuard = "fail"
        $priceOutputLockReason = "price_output_lock_parse_error"
        $kShieldMetadataGuard = "fail"
        $kShieldMetadataReason = "k_shield_metadata_parse_error"
    }
} else {
    $priceOutputLockGuard = "fail"
    $priceOutputLockReason = "price_output_lock_file_missing"
    $kShieldMetadataGuard = "fail"
    $kShieldMetadataReason = "k_shield_metadata_file_missing"
}

$closeReturnPctValue = $null
if (-not [string]::IsNullOrWhiteSpace($CloseReturnPct)) {
    try {
        $closeReturnPctValue = [double]$CloseReturnPct
    } catch {
        throw "Invalid -CloseReturnPct value. Provide numeric percent return (e.g. -0.92)."
    }
}
$hypothesisHitThreshold = -0.8
$hypothesisFailThreshold = 1.5
if ($null -ne $prophecyScoringRule) {
    if ($null -ne $prophecyScoringRule.hit_threshold_pct) {
        $hypothesisHitThreshold = [double]$prophecyScoringRule.hit_threshold_pct
    }
    if ($null -ne $prophecyScoringRule.fail_threshold_pct) {
        $hypothesisFailThreshold = [double]$prophecyScoringRule.fail_threshold_pct
    }
}
if (-not [string]::IsNullOrWhiteSpace($HitThresholdPct)) {
    try {
        $hypothesisHitThreshold = [double]$HitThresholdPct
    } catch {
        throw "Invalid -HitThresholdPct value."
    }
}
if (-not [string]::IsNullOrWhiteSpace($FailThresholdPct)) {
    try {
        $hypothesisFailThreshold = [double]$FailThresholdPct
    } catch {
        throw "Invalid -FailThresholdPct value."
    }
}
$metricToSuffix = {
    param([string]$metricName)
    $m = [string]$metricName
    if ($m -match "KOSPI") {
        return "kospi"
    }
    if ($m -match "BTC_BINANCE|BINANCE_BTC|BTC") {
        return "btc_binance"
    }
    $slug = $m.ToLower() -replace "[^a-z0-9]+", "_"
    $slug = $slug.Trim("_")
    if ([string]::IsNullOrWhiteSpace($slug)) {
        return "unknown"
    }
    return $slug
}
$postCloseEvalDecision = "PENDING_CLOSE"
$postCloseBandHit = $null
if ($null -ne $closeReturnPctValue) {
    if ([double]$closeReturnPctValue -le [double]$hypothesisHitThreshold) {
        $postCloseEvalDecision = "HIT"
    } elseif ([double]$closeReturnPctValue -ge [double]$hypothesisFailThreshold) {
        $postCloseEvalDecision = "FAIL"
    } else {
        $postCloseEvalDecision = "NEUTRAL_DRAW"
    }
    $normalizedBand = [string]$PredictedBand
    if ([string]::IsNullOrWhiteSpace($normalizedBand)) {
        $normalizedBand = "DOWN_STRONG"
    }
    $normalizedBand = $normalizedBand.Trim().ToUpper()
    if ($normalizedBand -eq "DOWN_STRONG") {
        $postCloseBandHit = ($postCloseEvalDecision -eq "HIT")
    } elseif ($normalizedBand -eq "UP_STRONG") {
        $postCloseBandHit = ($postCloseEvalDecision -eq "FAIL")
    } else {
        $postCloseBandHit = $null
    }
}
$primarySuffix = & $metricToSuffix $HypothesisMetric

$secondaryCloseReturnPctValue = $null
if (-not [string]::IsNullOrWhiteSpace($SecondaryCloseReturnPct)) {
    try {
        $secondaryCloseReturnPctValue = [double]$SecondaryCloseReturnPct
    } catch {
        throw "Invalid -SecondaryCloseReturnPct value."
    }
}
$secondaryHitThreshold = $hypothesisHitThreshold
$secondaryFailThreshold = $hypothesisFailThreshold
if (-not [string]::IsNullOrWhiteSpace($SecondaryHitThresholdPct)) {
    try {
        $secondaryHitThreshold = [double]$SecondaryHitThresholdPct
    } catch {
        throw "Invalid -SecondaryHitThresholdPct value."
    }
}
if (-not [string]::IsNullOrWhiteSpace($SecondaryFailThresholdPct)) {
    try {
        $secondaryFailThreshold = [double]$SecondaryFailThresholdPct
    } catch {
        throw "Invalid -SecondaryFailThresholdPct value."
    }
}
$secondaryPostCloseEvalDecision = "PENDING_CLOSE"
$secondaryPostCloseBandHit = $null
if ($null -ne $secondaryCloseReturnPctValue) {
    if ([double]$secondaryCloseReturnPctValue -le [double]$secondaryHitThreshold) {
        $secondaryPostCloseEvalDecision = "HIT"
    } elseif ([double]$secondaryCloseReturnPctValue -ge [double]$secondaryFailThreshold) {
        $secondaryPostCloseEvalDecision = "FAIL"
    } else {
        $secondaryPostCloseEvalDecision = "NEUTRAL_DRAW"
    }
    $secondaryBand = [string]$SecondaryPredictedBand
    if ([string]::IsNullOrWhiteSpace($secondaryBand)) {
        $secondaryBand = "DOWN_STRONG"
    }
    $secondaryBand = $secondaryBand.Trim().ToUpper()
    if ($secondaryBand -eq "DOWN_STRONG") {
        $secondaryPostCloseBandHit = ($secondaryPostCloseEvalDecision -eq "HIT")
    } elseif ($secondaryBand -eq "UP_STRONG") {
        $secondaryPostCloseBandHit = ($secondaryPostCloseEvalDecision -eq "FAIL")
    } else {
        $secondaryPostCloseBandHit = $null
    }
}
$secondarySuffix = $null
if (-not [string]::IsNullOrWhiteSpace($SecondaryHypothesisMetric)) {
    $secondarySuffix = & $metricToSuffix $SecondaryHypothesisMetric
}

# Build 5-business-day reliability preview using existing log + current decision.
$recentEvalDecisions = @()
if (Test-Path -LiteralPath $logPath) {
    try {
        $prevRows = Get-Content -LiteralPath $logPath -Encoding utf8
        foreach ($line in $prevRows) {
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }
            try {
                $obj = $line | ConvertFrom-Json
                $decision = [string]$obj.post_close_eval_decision
                if (-not [string]::IsNullOrWhiteSpace($decision)) {
                    $recentEvalDecisions += $decision.ToUpper()
                }
            } catch {
            }
        }
    } catch {
    }
}
if (-not [string]::IsNullOrWhiteSpace($postCloseEvalDecision)) {
    $recentEvalDecisions += $postCloseEvalDecision.ToUpper()
}
$recentEvalWindow = @($recentEvalDecisions | Select-Object -Last 5)
$weeklyHitCount = (@($recentEvalWindow | Where-Object { $_ -eq "HIT" })).Count
$weeklyFailCount = (@($recentEvalWindow | Where-Object { $_ -eq "FAIL" })).Count
$weeklyNeutralDrawCount = (@($recentEvalWindow | Where-Object { $_ -eq "NEUTRAL_DRAW" })).Count
$weeklyPendingCount = (@($recentEvalWindow | Where-Object { $_ -eq "PENDING_CLOSE" })).Count
$weeklyWindowCount = $recentEvalWindow.Count
$weeklyHitRate = if ($weeklyWindowCount -gt 0) { [math]::Round(($weeklyHitCount / $weeklyWindowCount), 4) } else { $null }
$weeklyFailRate = if ($weeklyWindowCount -gt 0) { [math]::Round(($weeklyFailCount / $weeklyWindowCount), 4) } else { $null }
$weeklyNeutralDrawRate = if ($weeklyWindowCount -gt 0) { [math]::Round(($weeklyNeutralDrawCount / $weeklyWindowCount), 4) } else { $null }
if (-not [string]::IsNullOrWhiteSpace($SecondaryHypothesisMetric) -and -not [string]::IsNullOrWhiteSpace($secondaryPostCloseEvalDecision)) {
    $recentEvalDecisions += $secondaryPostCloseEvalDecision.ToUpper()
}

Write-Host "[waiting-queue-check] Building Fact-Safe multi-lens brief..."
py scripts/build_fact_safe_multilens_brief.py --engine-id V2_Precision_MCP
if ($LASTEXITCODE -ne 0) {
    throw "Fact-Safe multi-lens brief build failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Emit billing invoice stub from env (.env / FACT_SAFE_INVOICE_*)..."
if (Test-Path -LiteralPath $billingInvoiceFromEnvScriptPath) {
    py scripts/emit_billing_invoice_from_env.py
    if ($LASTEXITCODE -ne 0) {
        throw "Emit billing invoice from env failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "billing invoice env emitter missing; skipped"
}

$billingInvoiceArg = @()
$billingInvoiceEffectivePath = $null
if (Test-Path -LiteralPath $billingInvoiceFromEnvPath) {
    $billingInvoiceArg = @("--invoice-input", $billingInvoiceFromEnvPath)
    $billingInvoiceEffectivePath = $billingInvoiceFromEnvPath
    Write-Host "[waiting-queue-check] Billing evidence will use invoice file: $billingInvoiceFromEnvPath"
}

Write-Host "[waiting-queue-check] Building billing evidence snapshot..."
if (Test-Path -LiteralPath $billingEvidenceScriptPath) {
    py scripts/report_billing_evidence_from_vllm.py --output $billingEvidencePath --period-label waiting_queue_monthly_check --input-usd-per-1k-tokens $inputUsdPer1k --output-usd-per-1k-tokens $outputUsdPer1k @billingInvoiceArg
    if ($LASTEXITCODE -ne 0) {
        throw "Billing evidence build failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "billing evidence script missing; skipped"
}

Write-Host "[waiting-queue-check] Building hallucination grounding eval snapshot..."
if (Test-Path -LiteralPath $hallucinationEvalScriptPath) {
    py scripts/report_hallucination_grounding_eval.py --output $hallucinationEvalPath --target-lane candidate --input-glob "$workspace\reports\constitution\btrack_pilot\vllm_ab_canary_run_*.json"
    if ($LASTEXITCODE -ne 0) {
        throw "Hallucination grounding eval build failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "hallucination eval script missing; skipped"
}

if ($enableHighSampleVllmEval) {
    if ((Test-Path -LiteralPath $expandedDatasetScriptPath) -and (Test-Path -LiteralPath $highSampleRepeatScriptPath)) {
        Write-Host "[waiting-queue-check] Building expanded vLLM AB dataset for high-sample eval..."
        py scripts/generate_vllm_ab_dataset_expanded.py --target-cases $highSampleCases --output $expandedDatasetPath
        if ($LASTEXITCODE -ne 0) {
            throw "Expanded vLLM AB dataset build failed with exit code $LASTEXITCODE"
        }

        Write-Host "[waiting-queue-check] Running high-sample vLLM canary repeat (allow-unavailable)..."
        py scripts/run_vllm_ab_canary_repeat.py --dataset-jsonl $expandedDatasetPath --runs $highSampleRuns --out-json $highSampleRepeatPath --allow-unavailable
        if ($LASTEXITCODE -ne 0) {
            throw "High-sample vLLM canary repeat failed with exit code $LASTEXITCODE"
        }

        Write-Host "[waiting-queue-check] Rebuilding hallucination grounding eval after high-sample run..."
        py scripts/report_hallucination_grounding_eval.py --output $hallucinationEvalPath --target-lane candidate --input-glob "$workspace\reports\constitution\btrack_pilot\vllm_ab_canary_run_*.json"
        if ($LASTEXITCODE -ne 0) {
            throw "Hallucination grounding eval (high-sample) failed with exit code $LASTEXITCODE"
        }
    } else {
        Add-SoftFailNote "high-sample vLLM eval enabled but required scripts are missing; skipped"
    }
}

Write-Host "[waiting-queue-check] Building cost watch monitor snapshot..."
if (Test-Path -LiteralPath $costWatchScriptPath) {
    py scripts/report_cost_watch_monitor.py --output $costWatchMonitorPath --billing-input $billingEvidencePath --hallucination-input $hallucinationEvalPath
    if ($LASTEXITCODE -ne 0) {
        throw "Cost watch monitor build failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "cost watch monitor script missing; skipped"
}

Write-Host "[waiting-queue-check] Independent lens v0 snapshots (myeongni, sasang, logos)..."
$lensFallbackArgs = @()
if ($AllowLensFallback) {
    Write-Host "[waiting-queue-check] WARN: AllowLensFallback enabled; lens fallback payloads may pass hard-gates." -ForegroundColor Yellow
    $lensFallbackArgs = @("--allow-fallback")
}
if (Test-Path -LiteralPath $lensMyeongniScriptPath) {
    py scripts/run_lens_myeongni.py @lensFallbackArgs
    if ($LASTEXITCODE -ne 0) {
        throw "run_lens_myeongni.py failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "run_lens_myeongni.py missing; skipped"
}
if (Test-Path -LiteralPath $lensSasangScriptPath) {
    py scripts/run_lens_sasang.py @lensFallbackArgs
    if ($LASTEXITCODE -ne 0) {
        throw "run_lens_sasang.py failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "run_lens_sasang.py missing; skipped"
}
if (Test-Path -LiteralPath $lensLogosScriptPath) {
    $logosBatchPath = Join-Path $workspace "data\logos\4lens_batch_sample.json"
    $logosFixturePath = Join-Path $workspace "tests\fixtures\logos_4lens_batch_minimal_v1.json"
    if (Test-Path -LiteralPath $logosBatchPath) {
        py scripts/run_lens_logos.py --batch-json $logosBatchPath @lensFallbackArgs
    } elseif (Test-Path -LiteralPath $logosFixturePath) {
        Write-Host "[waiting-queue-check] Logos: using tracked fixture (no data/logos/4lens_batch_sample.json)" -ForegroundColor DarkYellow
        py scripts/run_lens_logos.py --batch-json $logosFixturePath @lensFallbackArgs
    } else {
        if ($lensFallbackArgs.Count -gt 0) {
            py scripts/run_lens_logos.py @lensFallbackArgs
        } else {
            py scripts/run_lens_logos.py --allow-fallback
        }
    }
    if ($LASTEXITCODE -ne 0) {
        throw "run_lens_logos.py failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "run_lens_logos.py missing; skipped"
}
if (Test-Path -LiteralPath $lensFusionStubScriptPath) {
    py scripts/report_independent_lens_fusion_stub_v0.py
    if ($LASTEXITCODE -ne 0) {
        throw "report_independent_lens_fusion_stub_v0.py failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "report_independent_lens_fusion_stub_v0.py missing; skipped"
}
if (Test-Path -LiteralPath $lensShadowGateScriptPath) {
    py scripts/report_independent_lens_shadow_gate.py
    if ($LASTEXITCODE -ne 0) {
        throw "report_independent_lens_shadow_gate.py failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "report_independent_lens_shadow_gate.py missing; skipped"
}
if (Test-Path -LiteralPath $lensShadowMinorityMonthlyScriptPath) {
    py scripts/report_independent_lens_shadow_minority_monthly_v1.py
    if ($LASTEXITCODE -ne 0) {
        throw "report_independent_lens_shadow_minority_monthly_v1.py failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "report_independent_lens_shadow_minority_monthly_v1.py missing; skipped"
}

Write-Host "[waiting-queue-check] Running BTC regime-switch comparison (read-only sensor)..."
if (Test-Path -LiteralPath $regimeSwitchScriptPath) {
    py scripts/run_btc_time_machine_regime_switch_backtest.py
    if ($LASTEXITCODE -ne 0) {
        throw "BTC regime-switch comparison failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "regime switch backtest script missing; skipped"
}

if ($SkipNightWatchmanHarness) {
    Write-Host "[waiting-queue-check] Skipping Night Watchman harness guard by flag."
} elseif (-not (Test-Path -LiteralPath "$workspace\scripts\night_watchman_harness_v1.ps1")) {
    Add-SoftFailNote "Night Watchman harness script missing; skipped"
} else {
    Write-Host "[waiting-queue-check] Running Night Watchman harness guard..."
    powershell -ExecutionPolicy Bypass -File "$workspace\scripts\night_watchman_harness_v1.ps1" `
        -ConfigPath "$workspace\scripts\configs\night_watchman_harness_v1.json"
    if ($LASTEXITCODE -ne 0) {
        throw "Night Watchman harness guard failed with exit code $LASTEXITCODE"
    }
}

$highReliabilityDecision = $null
if (Test-Path -LiteralPath $highReliabilityGatePath) {
    try {
        $hrObj = Get-Content -LiteralPath $highReliabilityGatePath -Encoding utf8 | ConvertFrom-Json
        $highReliabilityDecision = [string]$hrObj.decision
    } catch {
        $highReliabilityDecision = "parse_error"
    }
}

$highReliabilityDecisionEffective = $highReliabilityDecision
$highReliabilityGateEffective = "pass"
if ($overlapDriftAlert -and ($highReliabilityDecision -eq "PASS")) {
    $highReliabilityDecisionEffective = "HOLD"
    $highReliabilityGateEffective = "hold_by_overlap_drift"
}

$regimeSwitchRule = $null
$regimeSwitchDeltaNet = $null
$regimeSwitchDeltaPf = $null
$regimeSwitchDeltaWorstMdd = $null
$regimeSwitchAdvisory = "sensor_unavailable"
$regimeSwitchAdvisoryReason = "report_missing_or_parse_error"
if (Test-Path -LiteralPath $regimeSwitchReportPath) {
    try {
        $regimeObj = Get-Content -LiteralPath $regimeSwitchReportPath -Encoding utf8 | ConvertFrom-Json
        $regimeSwitchRule = [string]$regimeObj.regime_switch.rule
        $regimeSwitchDeltaNet = $regimeObj.delta_regime_switch_minus_base.net_return_pct_sum
        $regimeSwitchDeltaPf = $regimeObj.delta_regime_switch_minus_base.profit_factor_weighted_by_samples
        $regimeSwitchDeltaWorstMdd = $regimeObj.delta_regime_switch_minus_base.max_drawdown_pct_worst_year
        $hasAllRegimeDeltas = ($null -ne $regimeSwitchDeltaNet) -and ($null -ne $regimeSwitchDeltaPf) -and ($null -ne $regimeSwitchDeltaWorstMdd)
        if ($hasAllRegimeDeltas) {
            $deltaNetPos = ([double]$regimeSwitchDeltaNet -gt 0.0)
            $deltaPfPos = ([double]$regimeSwitchDeltaPf -gt 0.0)
            $deltaMddImproved = ([double]$regimeSwitchDeltaWorstMdd -lt 0.0)
            if ($deltaNetPos -and $deltaPfPos -and $deltaMddImproved) {
                $regimeSwitchAdvisory = "prefer_switch_profile"
                $regimeSwitchAdvisoryReason = "delta_positive_net_pf_and_lower_mdd"
            } elseif (([double]$regimeSwitchDeltaNet -lt 0.0) -or ([double]$regimeSwitchDeltaPf -lt 0.0) -or ([double]$regimeSwitchDeltaWorstMdd -gt 0.0)) {
                $regimeSwitchAdvisory = "review_switch_profile"
                $regimeSwitchAdvisoryReason = "at_least_one_delta_degraded"
            } else {
                $regimeSwitchAdvisory = "mixed_signal_keep_observe"
                $regimeSwitchAdvisoryReason = "delta_direction_not_unanimous"
            }
        } else {
            $regimeSwitchAdvisory = "sensor_unavailable"
            $regimeSwitchAdvisoryReason = "delta_fields_incomplete"
        }
    } catch {
        $regimeSwitchRule = "parse_error"
        $regimeSwitchAdvisory = "sensor_unavailable"
        $regimeSwitchAdvisoryReason = "report_parse_error"
    }
}

$costWatchClaimHallucination = $null
$costWatchClaimMargin = $null
$costWatchBlockingReasons = $null
$costWatchBillingAuditReady = $null
$costWatchBillingSourceTier = $null
if (Test-Path -LiteralPath $costWatchMonitorPath) {
    try {
        $cwObj = Get-Content -LiteralPath $costWatchMonitorPath -Encoding utf8 | ConvertFrom-Json
        $costWatchClaimHallucination = $cwObj.claim_guardrails.can_claim_hallucination_zero
        $costWatchClaimMargin = $cwObj.claim_guardrails.can_claim_margin_uplift_50
        $costWatchBlockingReasons = $cwObj.claim_guardrails.blocking_reasons
        $costWatchBillingAuditReady = $cwObj.billing.invoice_audit_ready
        $costWatchBillingSourceTier = [string]$cwObj.billing.source_tier
    } catch {
        $costWatchBlockingReasons = @("cost_watch_parse_error")
    }
}

$dualRegimeStateKpi = $null
$dualRegimeStateSource = $null
$dualRegimeStatePresent = $null
$dualRegimeStateClampCount = $null
$dualRegimeStateSampleCount = $null
$dualRegimeStateClampRatio = $null
if (Test-Path -LiteralPath $latestKpiPath) {
    try {
        $kpiObj = Get-Content -LiteralPath $latestKpiPath -Encoding utf8 | ConvertFrom-Json
        $dk = $kpiObj.dual_regime_state_kpi
        if ($null -ne $dk) {
            $dualRegimeStateKpi = $dk
            $dualRegimeStateSource = [string]$dk.state_id_source
            $dualRegimeStatePresent = [bool]$dk.state_id_present
            if ($null -ne $dk.clamp_count) {
                $dualRegimeStateClampCount = [int]$dk.clamp_count
            } elseif ($null -ne $dk.signal_registry_clamped) {
                $dualRegimeStateClampCount = if ([bool]$dk.signal_registry_clamped) { 1 } else { 0 }
            }
            if ($null -ne $dk.sample_count) {
                $dualRegimeStateSampleCount = [int]$dk.sample_count
            } else {
                $dualRegimeStateSampleCount = 1
            }
            if (($null -ne $dualRegimeStateClampCount) -and ($null -ne $dualRegimeStateSampleCount) -and ($dualRegimeStateSampleCount -gt 0)) {
                $dualRegimeStateClampRatio = [math]::Round(($dualRegimeStateClampCount / $dualRegimeStateSampleCount), 6)
            }
        }
    } catch {
    }
}

# Fallback wiring: when latest_kpi dual_regime_state_kpi is missing,
# recover state-signal inputs from the most recent scoring distribution snapshot.
if (($null -eq $dualRegimeStateKpi) -and (Test-Path -LiteralPath $scoringDistributionPath)) {
    try {
        $distObj = Get-Content -LiteralPath $scoringDistributionPath -Encoding utf8 | ConvertFrom-Json
        $drAll = $distObj.dual_regime_state.all
        if ($null -ne $drAll) {
            $sampleSize = $null
            if ($null -ne $drAll.sample_size) {
                $sampleSize = [int]$drAll.sample_size
            }
            $presentRate = $null
            if ($null -ne $drAll.state_id_present_rate) {
                $presentRate = [double]$drAll.state_id_present_rate
            }
            $clampRate = $null
            if ($null -ne $drAll.clamp_rate) {
                $clampRate = [double]$drAll.clamp_rate
            }

            if (($null -ne $sampleSize) -and ($sampleSize -gt 0)) {
                $dualRegimeStateSource = [string]$drAll.top_source
                if ([string]::IsNullOrWhiteSpace($dualRegimeStateSource)) {
                    $dualRegimeStateSource = "none"
                }
                if ($null -ne $presentRate) {
                    $dualRegimeStatePresent = ([double]$presentRate -gt 0.0)
                }
                if ($null -ne $drAll.clamp_count) {
                    $dualRegimeStateClampCount = [int]$drAll.clamp_count
                }
                $dualRegimeStateSampleCount = $sampleSize
                if ($null -ne $clampRate) {
                    $dualRegimeStateClampRatio = [math]::Round([double]$clampRate, 6)
                } elseif (($null -ne $dualRegimeStateClampCount) -and ($dualRegimeStateSampleCount -gt 0)) {
                    $dualRegimeStateClampRatio = [math]::Round(($dualRegimeStateClampCount / $dualRegimeStateSampleCount), 6)
                }
                $dualRegimeStateKpi = @{
                    state_id_source = $dualRegimeStateSource
                    state_id_present = $dualRegimeStatePresent
                    clamp_count = $dualRegimeStateClampCount
                    sample_count = $dualRegimeStateSampleCount
                    clamp_ratio = $dualRegimeStateClampRatio
                    source = "scoring_distribution_fallback"
                }
            }
        }
    } catch {
    }
}

$dualRegimeAlertLevel = "insufficient_data"
$dualRegimeAlertReason = "state_kpi_missing"
if (($null -ne $dualRegimeStateSampleCount) -and ($dualRegimeStateSampleCount -gt 0)) {
    if (($dualRegimeStateSource -eq "none") -and (-not [bool]$dualRegimeStatePresent)) {
        $dualRegimeAlertLevel = "state_signal_not_wired"
        $dualRegimeAlertReason = "top_source_none_and_state_missing"
    } elseif (($null -ne $dualRegimeStateClampRatio) -and ([double]$dualRegimeStateClampRatio -ge 0.6)) {
        $dualRegimeAlertLevel = "state_clamp_high_tight_mode"
        $dualRegimeAlertReason = "clamp_ratio_ge_0.6"
    } elseif (($null -ne $dualRegimeStateClampRatio) -and ([double]$dualRegimeStateClampRatio -ge 0.3)) {
        $dualRegimeAlertLevel = "state_clamp_active_review_thresholds"
        $dualRegimeAlertReason = "clamp_ratio_ge_0.3"
    } else {
        $dualRegimeAlertLevel = "state_clamp_stable"
        $dualRegimeAlertReason = "clamp_ratio_lt_0.3"
    }
}

$logRow = @{
    checked_at_utc = $checkedAt
    bundle_mode = $bundleMode
    allow_lens_fallback = [bool]$AllowLensFallback
    cross_ref_test = "pass"
    bundle_test = if ($SkipBundle) { "skipped" } else { "pass" }
    source_hunt_summary = "pass"
    source_hunt_summary_path = $sourceHuntSummaryPath
    promotion_gate = "pass"
    promotion_gate_path = $promotionGatePath
    decision_lock_ref = if (Test-Path -LiteralPath $decisionLockPath) { $decisionLockPath } else { $null }
    btrack_verified_gate = $btrackVerifiedGateStatus
    btrack_verified_gate_path = $btrackGatePath
    btrack_symbol_lane_gate = $btrackSymbolLaneGateStatus
    btrack_symbol_lane_gate_path = $symbolLaneGatePath
    symbol_lane_profile_compare_path = $symbolLaneProfileComparePath
    top_overlap_rate = $topOverlapRate
    delta_vs_prev_overlap = $deltaVsPrevOverlap
    overlap_drift_alert = $overlapDriftAlert
    overlap_drift_alert_threshold = $OverlapDriftAlertThreshold
    high_reliability_gate = $highReliabilityGateEffective
    high_reliability_gate_path = $highReliabilityGatePath
    high_reliability_decision = $highReliabilityDecisionEffective
    high_reliability_decision_raw = $highReliabilityDecision
    price_output_lock_guard = $priceOutputLockGuard
    price_output_locked = $priceOutputLocked
    price_output_lock_reason = $priceOutputLockReason
    prophecy_reliability_badge = $prophecyReliabilityBadge
    prophecy_high_reliability_decision = $prophecyDecision
    prophecy_core_decision = $prophecyCoreDecision
    prophecy_core_score = $prophecyCoreScore
    prophecy_k_shield_candidate = $prophecyKShieldCandidate
    prophecy_k_shield_candidate_max_drawdown_pct = $prophecyKShieldMdd
    hypothesis_hit_threshold_pct = $hypothesisHitThreshold
    hypothesis_fail_threshold_pct = $hypothesisFailThreshold
    hypothesis_metric = $HypothesisMetric
    market_venue = $MarketVenue
    predicted_band = $PredictedBand
    close_return_pct = $closeReturnPctValue
    post_close_eval_decision = $postCloseEvalDecision
    post_close_band_hit = $postCloseBandHit
    hypothesis_metric_secondary = if ([string]::IsNullOrWhiteSpace($SecondaryHypothesisMetric)) { $null } else { $SecondaryHypothesisMetric }
    market_venue_secondary = if ([string]::IsNullOrWhiteSpace($SecondaryMarketVenue)) { $null } else { $SecondaryMarketVenue }
    hypothesis_hit_threshold_pct_secondary = if ([string]::IsNullOrWhiteSpace($SecondaryHypothesisMetric)) { $null } else { $secondaryHitThreshold }
    hypothesis_fail_threshold_pct_secondary = if ([string]::IsNullOrWhiteSpace($SecondaryHypothesisMetric)) { $null } else { $secondaryFailThreshold }
    predicted_band_secondary = if ([string]::IsNullOrWhiteSpace($SecondaryHypothesisMetric)) { $null } else { $SecondaryPredictedBand }
    close_return_pct_secondary = $secondaryCloseReturnPctValue
    post_close_eval_decision_secondary = if ([string]::IsNullOrWhiteSpace($SecondaryHypothesisMetric)) { $null } else { $secondaryPostCloseEvalDecision }
    post_close_band_hit_secondary = if ([string]::IsNullOrWhiteSpace($SecondaryHypothesisMetric)) { $null } else { $secondaryPostCloseBandHit }
    weekly_reliability_window = $weeklyWindowCount
    weekly_reliability_hit = $weeklyHitCount
    weekly_reliability_fail = $weeklyFailCount
    weekly_reliability_neutral_draw = $weeklyNeutralDrawCount
    weekly_reliability_pending = $weeklyPendingCount
    weekly_reliability_hit_rate = $weeklyHitRate
    weekly_reliability_fail_rate = $weeklyFailRate
    weekly_reliability_neutral_draw_rate = $weeklyNeutralDrawRate
    k_shield_metadata_guard = $kShieldMetadataGuard
    k_shield_metadata_reason = $kShieldMetadataReason
    external_feed_validation_mode = $externalFeedValidationMode
    monthly_prophecy_path = $monthlyProphecyPath
    biblical_external_reality_locked_profile = $biblicalExternalRealityStatus
    biblical_external_dualgate_stability_path = $biblicalExternalDualgateStabilityPath
    biblical_fixed_commercial_ops_relaxed = $biblicalFixedCommercialOpsRelaxed
    runtime_risk_profile_path = $runtimeRiskProfilePath
    next_monthly_due_date = $nextMonthlyDue
    horizon_t30_date = $horizonT30
    horizon_t90_date = $horizonT90
    slack_delivery_status_path = $slackDeliveryStatusPath
    slack_delivery_log_path = $slackDeliveryLogPath
    billing_evidence_path = $billingEvidencePath
    billing_invoice_from_env_path = $billingInvoiceEffectivePath
    hallucination_eval_path = $hallucinationEvalPath
    high_sample_vllm_eval_enabled = $enableHighSampleVllmEval
    high_sample_cases = $highSampleCases
    high_sample_runs = $highSampleRuns
    high_sample_dataset_path = if ($enableHighSampleVllmEval) { $expandedDatasetPath } else { $null }
    high_sample_repeat_path = if ($enableHighSampleVllmEval) { $highSampleRepeatPath } else { $null }
    cost_watch_monitor_path = $costWatchMonitorPath
    cost_watch_claim_hallucination_zero = $costWatchClaimHallucination
    cost_watch_claim_margin_uplift_50 = $costWatchClaimMargin
    cost_watch_blocking_reasons = $costWatchBlockingReasons
    cost_watch_billing_invoice_audit_ready = $costWatchBillingAuditReady
    cost_watch_billing_source_tier = $costWatchBillingSourceTier
    walk_forward_use_backfilled_history = [bool]$UseWalkForwardBackfilledHistory
    walk_forward_backfill_start_date = if ([string]::IsNullOrWhiteSpace($WalkForwardBackfillStartDate)) { $null } else { $WalkForwardBackfillStartDate }
    walk_forward_backfill_end_date = if ([string]::IsNullOrWhiteSpace($WalkForwardBackfillEndDate)) { $null } else { $WalkForwardBackfillEndDate }
    walk_forward_history_source = if ($UseWalkForwardBackfilledHistory) { $walkForwardBackfilledHistoryPath } else { $walkForwardRawHistoryPath }
    general_explainability_quality_path = $generalExplainabilityQualityPath
    general_explainability_quality_gate = $generalExplainabilityQualityGate
    general_explainability_quality_reason = $generalExplainabilityQualityReason
    general_explainability_coverage_rate = $generalExplainabilityCoverageRate
    general_explainability_conflict_resolution_rate = $generalExplainabilityConflictRate
    general_explainability_reproducible_evidence_rate = $generalExplainabilityReproRate
    general_explainability_coverage_min = $generalExplainabilityCoverageMin
    general_explainability_conflict_min = $generalExplainabilityConflictMin
    general_explainability_repro_min = $generalExplainabilityReproMin
    strict_general_explainability_quality_gate = [bool]$StrictGeneralExplainabilityQualityGate
    regime_switch_report_path = $regimeSwitchReportPath
    regime_switch_rule = $regimeSwitchRule
    regime_switch_delta_net_return_pct_sum = $regimeSwitchDeltaNet
    regime_switch_delta_profit_factor_weighted = $regimeSwitchDeltaPf
    regime_switch_delta_max_drawdown_pct_worst_year = $regimeSwitchDeltaWorstMdd
    regime_switch_advisory = $regimeSwitchAdvisory
    regime_switch_advisory_reason = $regimeSwitchAdvisoryReason
    dual_regime_state_source = $dualRegimeStateSource
    dual_regime_state_present = $dualRegimeStatePresent
    dual_regime_state_clamp_count = $dualRegimeStateClampCount
    dual_regime_state_sample_count = $dualRegimeStateSampleCount
    dual_regime_state_clamp_ratio = $dualRegimeStateClampRatio
    dual_regime_alert_level = $dualRegimeAlertLevel
    dual_regime_alert_reason = $dualRegimeAlertReason
    dual_regime_state_kpi = $dualRegimeStateKpi
    runner = "scripts/run_waiting_queue_monthly_check.ps1"
}
$logRow["close_return_pct_$primarySuffix"] = $closeReturnPctValue
$logRow["post_close_eval_decision_$primarySuffix"] = $postCloseEvalDecision
$logRow["post_close_band_hit_$primarySuffix"] = $postCloseBandHit
if (-not [string]::IsNullOrWhiteSpace($secondarySuffix)) {
    $logRow["close_return_pct_$secondarySuffix"] = $secondaryCloseReturnPctValue
    $logRow["post_close_eval_decision_$secondarySuffix"] = $secondaryPostCloseEvalDecision
    $logRow["post_close_band_hit_$secondarySuffix"] = $secondaryPostCloseBandHit
}
$logRow | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath -Encoding utf8

Write-Host "[waiting-queue-check] Building fused calibration-30 report..."
if (Test-Path -LiteralPath $fusedCalibrationScriptPath) {
    py scripts/report_fused_paper_cycle_calibration_30.py --log-path $logPath
    if ($LASTEXITCODE -ne 0) {
        throw "Fused calibration-30 report build failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "fused calibration script missing; skipped"
}

$weeklySnapshot = @{
    generated_at_utc = ([DateTimeOffset]::UtcNow).ToString("o")
    schema = "trinity_weekly_reliability_snapshot_v1"
    source_log_path = $logPath
    hypothesis_metric = $HypothesisMetric
    market_venue = $MarketVenue
    hit_threshold_pct = $hypothesisHitThreshold
    fail_threshold_pct = $hypothesisFailThreshold
    window_size = $weeklyWindowCount
    hit = $weeklyHitCount
    fail = $weeklyFailCount
    neutral_draw = $weeklyNeutralDrawCount
    pending_close = $weeklyPendingCount
    hit_rate = $weeklyHitRate
    fail_rate = $weeklyFailRate
    neutral_draw_rate = $weeklyNeutralDrawRate
    latest_post_close_eval_decision = $postCloseEvalDecision
    latest_close_return_pct = $closeReturnPctValue
    primary_metric_suffix = $primarySuffix
    secondary_metric_suffix = $secondarySuffix
    latest_post_close_eval_decision_secondary = if ([string]::IsNullOrWhiteSpace($SecondaryHypothesisMetric)) { $null } else { $secondaryPostCloseEvalDecision }
    latest_close_return_pct_secondary = $secondaryCloseReturnPctValue
    dual_regime_state_source = $dualRegimeStateSource
    dual_regime_state_present = $dualRegimeStatePresent
    dual_regime_state_clamp_count = $dualRegimeStateClampCount
    dual_regime_state_sample_count = $dualRegimeStateSampleCount
    dual_regime_state_clamp_ratio = $dualRegimeStateClampRatio
    dual_regime_alert_level = $dualRegimeAlertLevel
    dual_regime_alert_reason = $dualRegimeAlertReason
}
$weeklySnapshot | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $weeklyReliabilitySnapshotPath -Encoding utf8

Write-Host "[waiting-queue-check] Building trinity scoring distribution snapshot..."
py scripts/report_trinity_scoring_distribution.py --log-path $logPath --output $scoringDistributionPath --metric $HypothesisMetric
if ($LASTEXITCODE -ne 0) {
    throw "Trinity scoring distribution build failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Building B-Track monthly brief snapshot (Top10 recommendation)..."
if ((Test-Path -LiteralPath $btrackMonthlyBriefBuilderPath) -and (Test-Path -LiteralPath $btrackRecommendationPackPath)) {
    py scripts/build_btrack_monthly_brief_from_recommendation.py --input $btrackRecommendationPackPath --write-monthly-snapshot
    if ($LASTEXITCODE -ne 0) {
        throw "B-Track monthly brief build failed with exit code $LASTEXITCODE"
    }
} elseif (-not (Test-Path -LiteralPath $btrackMonthlyBriefBuilderPath)) {
    Add-SoftFailNote "B-Track monthly brief builder script missing; skipped"
} else {
    Add-SoftFailNote "B-Track recommendation pack missing; skipped monthly brief build"
}

# Hysteresis gate: only escalate when the same override skew advisory persists.
$overrideSkewDecision = $null
$overrideSkewReason = $null
$overrideSkewStreak = 0
if (Test-Path -LiteralPath $scoringDistributionPath) {
    try {
        $distObj = Get-Content -LiteralPath $scoringDistributionPath -Encoding utf8 | ConvertFrom-Json
        $overrideSkewDecision = [string]$distObj.auto_hold_overrides.advisory.decision
        $overrideSkewReason = [string]$distObj.auto_hold_overrides.advisory.reason
    } catch {
        $overrideSkewDecision = $null
        $overrideSkewReason = "distribution_parse_error"
    }
}
if ($overrideSkewDecision -in @("override_skew_net_source_fallback", "override_skew_dual_regime_state_clamp")) {
    $overrideSkewStreakThreshold = 3
    if ($env:FACT_SAFE_OVERRIDE_SKEW_STREAK_THRESHOLD) {
        try {
            $overrideSkewStreakThreshold = [int]$env:FACT_SAFE_OVERRIDE_SKEW_STREAK_THRESHOLD
        } catch {
            $overrideSkewStreakThreshold = 3
        }
    }
    if ($overrideSkewStreakThreshold -lt 1) {
        $overrideSkewStreakThreshold = 1
    }
    $overrideSkewStreak = 1
    if (Test-Path -LiteralPath $logPath) {
        try {
            $prevRows = Get-Content -LiteralPath $logPath -Encoding utf8
            for ($idx = $prevRows.Count - 1; $idx -ge 0; $idx--) {
                $line = $prevRows[$idx]
                if ([string]::IsNullOrWhiteSpace($line)) { continue }
                try {
                    $obj = $line | ConvertFrom-Json
                    $prevDecision = [string]$obj.override_skew_decision
                    if ($prevDecision -eq $overrideSkewDecision) {
                        $overrideSkewStreak += 1
                        continue
                    }
                } catch {
                }
                break
            }
        } catch {
        }
    }
    if ($overrideSkewStreak -ge $overrideSkewStreakThreshold) {
        @{
            checked_at_utc = ([DateTimeOffset]::UtcNow).ToString("o")
            bundle_mode = $bundleMode
            cross_ref_test = "pass"
            bundle_test = if ($SkipBundle) { "skipped" } else { "pass" }
            auto_hold_promotion = $true
            high_reliability_decision_override = "HOLD"
            override_reason = "override_skew_hysteresis_streak_ge_threshold"
            override_trigger_type = "override_skew_advisory"
            override_priority = 80
            override_skew_decision = $overrideSkewDecision
            override_skew_reason = $overrideSkewReason
            override_skew_streak = $overrideSkewStreak
            override_skew_streak_threshold = $overrideSkewStreakThreshold
            runner = "scripts/run_waiting_queue_monthly_check.ps1"
        } | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath -Encoding utf8
        throw "Auto HOLD promotion triggered: override skew hysteresis decision=$overrideSkewDecision streak=$overrideSkewStreak threshold=$overrideSkewStreakThreshold"
    }
}

if ($priceOutputLockGuard -ne "pass") {
    throw "Price output lock guard failed: $priceOutputLockReason"
}
if ($kShieldMetadataGuard -ne "pass") {
    throw "K-shield metadata guard failed: $kShieldMetadataReason"
}

Write-Host "[waiting-queue-check] Broadcasting Fact-Safe summary..."
py scripts/broadcast_fact_safe_multilens_brief.py --strict-required
if ($LASTEXITCODE -ne 0) {
    throw "Fact-Safe broadcast build failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Sending Fact-Safe summary to Slack (if webhook configured)..."
py scripts/send_fact_safe_broadcast_to_slack.py
if ($LASTEXITCODE -ne 0) {
    throw "Fact-Safe Slack send failed with exit code $LASTEXITCODE"
}

# Auto HOLD promotion on persistent net_source fallback.
if (Test-Path -LiteralPath $slackDeliveryStatusPath) {
    try {
        $deliveryObj = Get-Content -LiteralPath $slackDeliveryStatusPath -Encoding utf8 | ConvertFrom-Json
        $fallbackEscalated = [bool]$deliveryObj.net_source_fallback_escalated
        $fallbackStreak = [int]($deliveryObj.net_source_fallback_streak | ForEach-Object { $_ })
        if ($fallbackEscalated) {
            @{
                checked_at_utc = ([DateTimeOffset]::UtcNow).ToString("o")
                bundle_mode = $bundleMode
                cross_ref_test = "pass"
                bundle_test = if ($SkipBundle) { "skipped" } else { "pass" }
                auto_hold_promotion = $true
                high_reliability_decision_override = "HOLD"
                override_reason = "net_source_fallback_streak_escalated"
                override_trigger_type = "net_source_fallback"
                override_priority = 100
                net_source_fallback_streak = $fallbackStreak
                skip_net_source_fallback_auto_hold = $skipNetSourceFallbackAutoHoldEffective
                slack_delivery_status_path = $slackDeliveryStatusPath
                runner = "scripts/run_waiting_queue_monthly_check.ps1"
            } | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath -Encoding utf8
            if (-not $skipNetSourceFallbackAutoHoldEffective) {
                throw "Auto HOLD promotion triggered: net_source fallback streak=$fallbackStreak"
            }
            Add-SoftFailNote "Net-source fallback auto-hold escalation observed but suppressed by SkipNetSourceFallbackAutoHold (streak=$fallbackStreak)"
        }
    } catch {
        if ($_.Exception.Message -like "Auto HOLD promotion triggered*") {
            throw
        }
    }
}

# Auto HOLD promotion on persistent high-tight dual regime clamp mode.
if ($dualRegimeAlertLevel -eq "state_clamp_high_tight_mode") {
    @{
        checked_at_utc = ([DateTimeOffset]::UtcNow).ToString("o")
        bundle_mode = $bundleMode
        cross_ref_test = "pass"
        bundle_test = if ($SkipBundle) { "skipped" } else { "pass" }
        auto_hold_promotion = $true
        high_reliability_decision_override = "HOLD"
        override_reason = "dual_regime_state_clamp_high_tight_mode"
        override_trigger_type = "dual_regime_state_clamp"
        override_priority = 90
        dual_regime_alert_level = $dualRegimeAlertLevel
        dual_regime_alert_reason = $dualRegimeAlertReason
        runner = "scripts/run_waiting_queue_monthly_check.ps1"
    } | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath -Encoding utf8
    throw "Auto HOLD promotion triggered: dual regime clamp high-tight mode"
}

Write-Host "[waiting-queue-check] Building insight effectiveness scoreboard..."
if (Test-Path -LiteralPath $insightScoreboardScriptPath) {
    py $insightScoreboardScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Insight effectiveness scoreboard build failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "insight effectiveness scoreboard script missing; skipped"
}

Write-Host "[waiting-queue-check] Running C2 Aegis baseline guardrail check..."
if (Test-Path -LiteralPath $c2GuardrailScriptPath) {
    py $c2GuardrailScriptPath --guardrail $c2GuardrailPath --current $c2CurrentScoreboardPath --out $c2GuardrailStatusPath
    if ($LASTEXITCODE -ne 0) {
        throw "C2 Aegis guardrail check failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "C2 Aegis guardrail script missing; skipped"
}

Write-Host "[waiting-queue-check] Building report_schema_v2 chain (from chain artifacts -> label KPI -> quality alert)..."
if (
    (Test-Path -LiteralPath $reportSchemaV2FromChainScriptPath) -and
    (Test-Path -LiteralPath $reportSchemaV2LabelKpiScriptPath) -and
    (Test-Path -LiteralPath $reportSchemaV2QualityAlertScriptPath)
) {
    py $reportSchemaV2FromChainScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "report_schema_v2 from-chain build failed with exit code $LASTEXITCODE"
    }
    py $reportSchemaV2LabelKpiScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "report_schema_v2 label KPI build failed with exit code $LASTEXITCODE"
    }
    py $reportSchemaV2QualityAlertScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "report_schema_v2 quality alert build failed with exit code $LASTEXITCODE"
    }
} else {
    Add-SoftFailNote "report_schema_v2 chain script(s) missing; skipped"
}

Write-Host "[waiting-queue-check] Building walk-forward eval + comparison report..."
if ((Test-Path -LiteralPath $walkForwardEvalScriptPath) -and (Test-Path -LiteralPath $evalComparisonScriptPath)) {
    $walkForwardHistoryForEval = $walkForwardRawHistoryPath
    if ($UseWalkForwardBackfilledHistory) {
        if (Test-Path -LiteralPath $walkForwardHistoryBuilderScriptPath) {
            $backfillArgs = @(
                "scripts/build_fusion_shadow_daily_history_v1.py",
                "--input-jsonl", $walkForwardRawHistoryPath,
                "--output-jsonl", $walkForwardBackfilledHistoryPath,
                "--backfill-leading"
            )
            if (-not [string]::IsNullOrWhiteSpace($WalkForwardBackfillStartDate)) {
                $backfillArgs += @("--start-date", $WalkForwardBackfillStartDate)
            }
            if (-not [string]::IsNullOrWhiteSpace($WalkForwardBackfillEndDate)) {
                $backfillArgs += @("--end-date", $WalkForwardBackfillEndDate)
            }
            py @backfillArgs
            if ($LASTEXITCODE -ne 0) {
                Add-SoftFailNote "walk-forward history backfill build failed with exit code $LASTEXITCODE; fallback to raw history"
            } elseif (Test-Path -LiteralPath $walkForwardBackfilledHistoryPath) {
                $walkForwardHistoryForEval = $walkForwardBackfilledHistoryPath
            } else {
                Add-SoftFailNote "walk-forward history backfill output missing; fallback to raw history"
            }
        } else {
            Add-SoftFailNote "walk-forward history backfill script missing; fallback to raw history"
        }
    }
    py scripts/eval_btrack_walk_forward_hit_rate_v1.py --recent-trading-days 30 --history-jsonl $walkForwardHistoryForEval --output $walkForwardEvalLatestPath
    if ($LASTEXITCODE -ne 0) {
        Add-SoftFailNote "walk-forward eval build failed with exit code $LASTEXITCODE; skipped comparison report"
    } else {
        py scripts/build_prophecy_eval_comparison_report_v1.py `
            --bear-json "$workspace\docs\final\artifacts\prophecy_hit_rate_eval_3way_bear_2026-04-17.json" `
            --neutral-json "$workspace\docs\final\artifacts\prophecy_hit_rate_eval_3way_neutral_2026-04-17.json" `
            --bull-json "$workspace\docs\final\artifacts\prophecy_hit_rate_eval_3way_bull_2026-04-17.json" `
            --walk-forward-json $walkForwardEvalLatestPath `
            --output $evalComparisonLatestPath
        if ($LASTEXITCODE -ne 0) {
            Add-SoftFailNote "prophecy eval comparison report build failed with exit code $LASTEXITCODE"
        } elseif (Test-Path -LiteralPath $evalComparisonLatestPath) {
            try {
                $cmpObj = Get-Content -LiteralPath $evalComparisonLatestPath -Raw -Encoding utf8 | ConvertFrom-Json
                $wfRatio = $cmpObj.walk_forward.synthetic_backfill_ratio
                if ($null -ne $wfRatio) {
                    $wfRatioValue = [double]$wfRatio
                    if ($wfRatioValue -gt [double]$walkForwardSyntheticRatioWarnThreshold) {
                        Add-SoftFailNote ("walk-forward synthetic_backfill_ratio high ({0:N4} > {1:N4}); increase raw daily signal density" -f $wfRatioValue, $walkForwardSyntheticRatioWarnThreshold)
                    }
                }
            } catch {
                Add-SoftFailNote "walk-forward synthetic ratio parse failed in comparison report"
            }
        }
    }
} else {
    Add-SoftFailNote "walk-forward/comparison script missing; skipped"
}

Write-Host "[waiting-queue-check] Wrote log: $logPath"
if ($softFailNotes.Count -gt 0) {
    $walkForwardBackfillState = if ($UseWalkForwardBackfilledHistory) { "enabled" } else { "disabled" }
    $sitrep = @()
    $sitrep += ("[{0}] waiting_queue_daily soft-fail summary" -f ([DateTimeOffset]::UtcNow.ToString("o")))
    foreach ($n in $softFailNotes) {
        $sitrep += ("- WARN: {0}" -f $n)
    }
    $sitrep += ("- allow_lens_fallback: {0}" -f $allowLensFallbackState)
    $sitrep += ("- walk_forward_backfilled_history: {0}" -f $walkForwardBackfillState)
    $sitrep += "- policy: soft-fail (non-core optional tasks)"
    $sitrep += ""
    Add-Content -LiteralPath $dailySitrepPath -Value ($sitrep -join [Environment]::NewLine) -Encoding utf8
    Write-Host "[waiting-queue-check] Soft-fail notes written: $dailySitrepPath"
}
Write-Host "[waiting-queue-check] Completed successfully."
