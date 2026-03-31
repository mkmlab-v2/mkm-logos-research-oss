param(
    [switch]$SkipBundle,
    [double]$OverlapDriftAlertThreshold = -0.05
)

$ErrorActionPreference = "Stop"

$workspace = "C:\workspace"
Set-Location $workspace

$logPath = "C:\workspace\docs\final\artifacts\waiting_queue_monthly_check_log.jsonl"
$sourceHuntSummaryPath = "C:\workspace\docs\final\artifacts\entry16_source_hunt_summary.json"
$promotionGatePath = "C:\workspace\docs\final\artifacts\entry16_promotion_gate.json"
$decisionLockPath = "C:\workspace\docs\final\artifacts\entry16_manual_promotion_decision_lock_latest.json"
$highReliabilityGatePath = "C:\workspace\docs\final\artifacts\high_reliability_mode_gate_latest.json"
$monthlyProphecyPath = "C:\workspace\docs\final\artifacts\prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
$runtimeRiskProfilePath = "C:\workspace\projects\bitcoin-trading\memory\v2\risk\risk_profile_fact_safe_latest.json"
$symbolLaneProfileComparePath = "C:\workspace\reports\constitution\btrack_pilot\symbol_lane_profile_compare_latest.json"
$btrackGatePath = "C:\workspace\reports\constitution\btrack_pilot\btrack_promotion_gate_anchor_verified_only_latest.json"
$symbolLaneGatePath = "C:\workspace\reports\constitution\btrack_pilot\symbol_lane_gate_latest.json"
$slackDeliveryStatusPath = "C:\workspace\reports\constitution\btrack_pilot\fact_safe_slack_delivery_latest.json"
$slackDeliveryLogPath = "C:\workspace\reports\constitution\btrack_pilot\fact_safe_slack_delivery_log.jsonl"
$costWatchMonitorPath = "C:\workspace\docs\final\artifacts\cost_watch_monitor_latest.json"
$billingEvidencePath = "C:\workspace\docs\final\artifacts\billing_evidence_latest.json"
$hallucinationEvalPath = "C:\workspace\docs\final\artifacts\hallucination_grounding_eval_latest.json"
$expandedDatasetPath = "C:\workspace\reports\constitution\btrack_pilot\vllm_ab_dataset_expanded_latest.jsonl"
$highSampleRepeatPath = "C:\workspace\reports\constitution\btrack_pilot\vllm_ab_canary_repeat_high_sample_latest.json"
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
    & "C:\workspace\projects\bitcoin-trading\ops\v2\tasks\run_prophecy_alignment_pytest.ps1"
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

Write-Host "[waiting-queue-check] Running B-Track verified gate+lock..."
& "C:\workspace\scripts\run_btrack_gate_and_lock.ps1"
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

Write-Host "[waiting-queue-check] Running BTC time-machine sweep (evidence scaling)..."
py scripts/run_btc_time_machine_backtest_sweep.py
if ($LASTEXITCODE -ne 0) {
    throw "BTC time-machine sweep failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Generating 2026 monthly KOSPI/BTC prophecy (fact-safe)..."
py scripts/generate_2026_monthly_kospi_btc_prophecy.py
if ($LASTEXITCODE -ne 0) {
    throw "2026 monthly KOSPI/BTC prophecy generation failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Syncing trinity risk governor to runtime risk_profile..."
py scripts/sync_fact_safe_risk_profile.py --prophecy $monthlyProphecyPath --output $runtimeRiskProfilePath
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
    } catch {
        $priceOutputLockGuard = "fail"
        $priceOutputLockReason = "price_output_lock_parse_error"
    }
} else {
    $priceOutputLockGuard = "fail"
    $priceOutputLockReason = "price_output_lock_file_missing"
}

Write-Host "[waiting-queue-check] Building Fact-Safe multi-lens brief..."
py scripts/build_fact_safe_multilens_brief.py --engine-id V2_Precision_MCP
if ($LASTEXITCODE -ne 0) {
    throw "Fact-Safe multi-lens brief build failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Building billing evidence snapshot..."
py scripts/report_billing_evidence_from_vllm.py --output $billingEvidencePath --period-label waiting_queue_monthly_check --input-usd-per-1k-tokens $inputUsdPer1k --output-usd-per-1k-tokens $outputUsdPer1k
if ($LASTEXITCODE -ne 0) {
    throw "Billing evidence build failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Building hallucination grounding eval snapshot..."
py scripts/report_hallucination_grounding_eval.py --output $hallucinationEvalPath --target-lane candidate --input-glob "C:\workspace\reports\constitution\btrack_pilot\vllm_ab_canary_run_*.json"
if ($LASTEXITCODE -ne 0) {
    throw "Hallucination grounding eval build failed with exit code $LASTEXITCODE"
}

if ($enableHighSampleVllmEval) {
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
    py scripts/report_hallucination_grounding_eval.py --output $hallucinationEvalPath --target-lane candidate --input-glob "C:\workspace\reports\constitution\btrack_pilot\vllm_ab_canary_run_*.json"
    if ($LASTEXITCODE -ne 0) {
        throw "Hallucination grounding eval (high-sample) failed with exit code $LASTEXITCODE"
    }
}

Write-Host "[waiting-queue-check] Building cost watch monitor snapshot..."
py scripts/report_cost_watch_monitor.py --output $costWatchMonitorPath --billing-input $billingEvidencePath --hallucination-input $hallucinationEvalPath
if ($LASTEXITCODE -ne 0) {
    throw "Cost watch monitor build failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-check] Running Night Watchman harness guard..."
powershell -ExecutionPolicy Bypass -File "C:\workspace\scripts\night_watchman_harness_v1.ps1" `
    -ConfigPath "C:\workspace\scripts\configs\night_watchman_harness_v1.json"
if ($LASTEXITCODE -ne 0) {
    throw "Night Watchman harness guard failed with exit code $LASTEXITCODE"
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

@{
    checked_at_utc = $checkedAt
    bundle_mode = $bundleMode
    cross_ref_test = "pass"
    bundle_test = if ($SkipBundle) { "skipped" } else { "pass" }
    source_hunt_summary = "pass"
    source_hunt_summary_path = $sourceHuntSummaryPath
    promotion_gate = "pass"
    promotion_gate_path = $promotionGatePath
    decision_lock_ref = if (Test-Path -LiteralPath $decisionLockPath) { $decisionLockPath } else { $null }
    btrack_verified_gate = "pass"
    btrack_verified_gate_path = $btrackGatePath
    btrack_symbol_lane_gate = "pass"
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
    monthly_prophecy_path = $monthlyProphecyPath
    runtime_risk_profile_path = $runtimeRiskProfilePath
    next_monthly_due_date = $nextMonthlyDue
    horizon_t30_date = $horizonT30
    horizon_t90_date = $horizonT90
    slack_delivery_status_path = $slackDeliveryStatusPath
    slack_delivery_log_path = $slackDeliveryLogPath
    billing_evidence_path = $billingEvidencePath
    hallucination_eval_path = $hallucinationEvalPath
    high_sample_vllm_eval_enabled = $enableHighSampleVllmEval
    high_sample_cases = $highSampleCases
    high_sample_runs = $highSampleRuns
    high_sample_dataset_path = if ($enableHighSampleVllmEval) { $expandedDatasetPath } else { $null }
    high_sample_repeat_path = if ($enableHighSampleVllmEval) { $highSampleRepeatPath } else { $null }
    cost_watch_monitor_path = $costWatchMonitorPath
    runner = "scripts/run_waiting_queue_monthly_check.ps1"
} | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath -Encoding utf8

if ($priceOutputLockGuard -ne "pass") {
    throw "Price output lock guard failed: $priceOutputLockReason"
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
                auto_hold_promotion = $true
                high_reliability_decision_override = "HOLD"
                override_reason = "net_source_fallback_streak_escalated"
                net_source_fallback_streak = $fallbackStreak
                slack_delivery_status_path = $slackDeliveryStatusPath
                runner = "scripts/run_waiting_queue_monthly_check.ps1"
            } | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath -Encoding utf8
            throw "Auto HOLD promotion triggered: net_source fallback streak=$fallbackStreak"
        }
    } catch {
        if ($_.Exception.Message -like "Auto HOLD promotion triggered*") {
            throw
        }
    }
}

Write-Host "[waiting-queue-check] Wrote log: $logPath"
Write-Host "[waiting-queue-check] Completed successfully."
