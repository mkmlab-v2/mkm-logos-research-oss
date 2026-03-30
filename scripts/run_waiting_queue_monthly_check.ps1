param(
    [switch]$SkipBundle
)

$ErrorActionPreference = "Stop"

$workspace = "C:\workspace"
Set-Location $workspace

$logPath = "C:\workspace\docs\final\artifacts\waiting_queue_monthly_check_log.jsonl"
$sourceHuntSummaryPath = "C:\workspace\docs\final\artifacts\entry16_source_hunt_summary.json"
$promotionGatePath = "C:\workspace\docs\final\artifacts\entry16_promotion_gate.json"
$checkedAt = [DateTimeOffset]::UtcNow.ToString("o")
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

@{
    checked_at_utc = $checkedAt
    bundle_mode = $bundleMode
    cross_ref_test = "pass"
    bundle_test = if ($SkipBundle) { "skipped" } else { "pass" }
    source_hunt_summary = "pass"
    source_hunt_summary_path = $sourceHuntSummaryPath
    promotion_gate = "pass"
    promotion_gate_path = $promotionGatePath
    runner = "scripts/run_waiting_queue_monthly_check.ps1"
} | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath -Encoding utf8

Write-Host "[waiting-queue-check] Wrote log: $logPath"
Write-Host "[waiting-queue-check] Completed successfully."
