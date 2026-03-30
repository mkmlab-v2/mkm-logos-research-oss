param(
    [switch]$SkipBundle
)

$ErrorActionPreference = "Stop"

$workspace = "C:\workspace"
Set-Location $workspace

$logPath = "C:\workspace\docs\final\artifacts\waiting_queue_monthly_check_log.jsonl"
$sourceHuntSummaryPath = "C:\workspace\docs\final\artifacts\entry16_source_hunt_summary.json"
$promotionGatePath = "C:\workspace\docs\final\artifacts\entry16_promotion_gate.json"
$btrackGatePath = "C:\workspace\reports\constitution\btrack_pilot\btrack_promotion_gate_anchor_verified_only_latest.json"
$symbolLaneGatePath = "C:\workspace\reports\constitution\btrack_pilot\symbol_lane_gate_latest.json"
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

@{
    checked_at_utc = $checkedAt
    bundle_mode = $bundleMode
    cross_ref_test = "pass"
    bundle_test = if ($SkipBundle) { "skipped" } else { "pass" }
    source_hunt_summary = "pass"
    source_hunt_summary_path = $sourceHuntSummaryPath
    promotion_gate = "pass"
    promotion_gate_path = $promotionGatePath
    btrack_verified_gate = "pass"
    btrack_verified_gate_path = $btrackGatePath
    btrack_symbol_lane_gate = "pass"
    btrack_symbol_lane_gate_path = $symbolLaneGatePath
    next_monthly_due_date = $nextMonthlyDue
    horizon_t30_date = $horizonT30
    horizon_t90_date = $horizonT90
    runner = "scripts/run_waiting_queue_monthly_check.ps1"
} | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath -Encoding utf8

Write-Host "[waiting-queue-check] Wrote log: $logPath"
Write-Host "[waiting-queue-check] Completed successfully."
