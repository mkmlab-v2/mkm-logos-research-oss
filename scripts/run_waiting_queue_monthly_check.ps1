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
$symbolLaneProfileComparePath = "C:\workspace\reports\constitution\btrack_pilot\symbol_lane_profile_compare_latest.json"
$btrackGatePath = "C:\workspace\reports\constitution\btrack_pilot\btrack_promotion_gate_anchor_verified_only_latest.json"
$symbolLaneGatePath = "C:\workspace\reports\constitution\btrack_pilot\symbol_lane_gate_latest.json"
$slackDeliveryStatusPath = "C:\workspace\reports\constitution\btrack_pilot\fact_safe_slack_delivery_latest.json"
$slackDeliveryLogPath = "C:\workspace\reports\constitution\btrack_pilot\fact_safe_slack_delivery_log.jsonl"
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

Write-Host "[waiting-queue-check] Building Fact-Safe multi-lens brief..."
py scripts/build_fact_safe_multilens_brief.py --engine-id V2_Precision_MCP
if ($LASTEXITCODE -ne 0) {
    throw "Fact-Safe multi-lens brief build failed with exit code $LASTEXITCODE"
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
    next_monthly_due_date = $nextMonthlyDue
    horizon_t30_date = $horizonT30
    horizon_t90_date = $horizonT90
    slack_delivery_status_path = $slackDeliveryStatusPath
    slack_delivery_log_path = $slackDeliveryLogPath
    runner = "scripts/run_waiting_queue_monthly_check.ps1"
} | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath -Encoding utf8

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

Write-Host "[waiting-queue-check] Wrote log: $logPath"
Write-Host "[waiting-queue-check] Completed successfully."
