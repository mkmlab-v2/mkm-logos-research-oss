param(
    [string]$Phase1Mode = "weekly_lite"
)

$ErrorActionPreference = "Stop"

$workspace = "C:\workspace"
Set-Location $workspace

$maint = [System.Environment]::GetEnvironmentVariable("MKM_WORKSPACE_MAINTENANCE")
if ($maint -and ($maint.Trim().ToLower() -in @("1", "true", "yes", "on"))) {
    Write-Host "[ops-fusion] SKIP: MKM_WORKSPACE_MAINTENANCE active" -ForegroundColor Yellow
    exit 0
}

Write-Host "[ops-fusion] Step 1/7: waiting_queue_btc_binance_daily"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_waiting_queue_btc_binance_daily.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "run_waiting_queue_btc_binance_daily.ps1 failed with exit code $LASTEXITCODE"
}

Write-Host "[ops-fusion] Step 2/7: fused_quant_pixel_sop"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_fused_quant_pixel_sop.ps1" -Phase1Mode $Phase1Mode
if ($LASTEXITCODE -ne 0) {
    throw "run_fused_quant_pixel_sop.ps1 failed with exit code $LASTEXITCODE"
}

Write-Host "[ops-fusion] Step 3/7: waiting_queue_monthly_check (includes C2 guardrail)"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_waiting_queue_monthly_check.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "run_waiting_queue_monthly_check.ps1 failed with exit code $LASTEXITCODE"
}

Write-Host "[ops-fusion] Step 4/7: BTC-only trinity distribution refresh"
py "C:\workspace\scripts\report_trinity_scoring_distribution.py" --metric BTC_BINANCE_D1_RETURN_PCT --output "C:\workspace\docs\final\artifacts\trinity_scoring_distribution_btc_latest.json"
if ($LASTEXITCODE -ne 0) {
    throw "report_trinity_scoring_distribution.py failed with exit code $LASTEXITCODE"
}

$c2Path = "C:\workspace\docs\final\artifacts\c2_aegis_guardrail_status_latest.json"
$trinityPath = "C:\workspace\docs\final\artifacts\trinity_scoring_distribution_btc_latest.json"
$summary = [ordered]@{
    schema = "ops_fusion_cycle_status_v2"
    generated_at_utc = ([DateTimeOffset]::UtcNow).ToString("o")
    runner = "projects/bitcoin-trading/ops/windows-rehearsal/run_ops_fusion_cycle.ps1"
    phase1_mode = $Phase1Mode
    c2_guardrail_status_path = $c2Path
    trinity_btc_distribution_path = $trinityPath
}

$overallOk = $false
$overallReason = "not_evaluated"

if (-not (Test-Path -LiteralPath $trinityPath)) {
    $overallReason = "missing_trinity_json"
} elseif (-not (Test-Path -LiteralPath $c2Path)) {
    $overallReason = "missing_c2_json"
} else {
    try {
        $c2 = Get-Content -LiteralPath $c2Path -Raw -Encoding utf8 | ConvertFrom-Json
        $summary["c2_status"] = [string]$c2.status
        $summary["c2_delta_vs_baseline"] = $c2.delta_vs_baseline
        $summary["c2_structural_break_alert"] = [bool]$c2.structural_break_alert
        $st = [string]$c2.status
        $breakAlert = $false
        if ($c2.PSObject.Properties.Name -contains "structural_break_alert") {
            $breakAlert = [bool]$c2.structural_break_alert
        }
        if ([string]::IsNullOrWhiteSpace($st)) {
            $overallReason = "c2_status_empty"
        } elseif ($breakAlert) {
            $overallReason = "c2_structural_break_alert"
        } elseif ($st -like "*RED*") {
            $overallReason = "c2_status_red"
        } else {
            $overallOk = $true
            $overallReason = "c2_green_or_yellow_no_structural_break"
        }
    } catch {
        $overallReason = "c2_parse_error"
    }
}

$summary["overall_ok"] = $overallOk
$summary["overall_ok_reason"] = $overallReason

$outPath = "C:\workspace\docs\final\artifacts\ops_fusion_cycle_status_latest.json"
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outPath -Encoding utf8
Write-Host "[ops-fusion] WROTE: $outPath"

Write-Host "[ops-fusion] Step 5/7: showroom public bundle (public-event.v1 + observability)"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\build_showroom_display_bundle.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "build_showroom_display_bundle.ps1 failed with exit code $LASTEXITCODE"
}

Write-Host "[ops-fusion] Step 6/7: validate_showroom_public_bundle.py"
py "C:\workspace\scripts\validate_showroom_public_bundle.py" "C:\workspace\docs\final\artifacts\showroom_public_bundle_v1.json"
if ($LASTEXITCODE -ne 0) {
    throw "validate_showroom_public_bundle.py failed with exit code $LASTEXITCODE"
}

$publishIngest = [Environment]::GetEnvironmentVariable("SHOWROOM_PUBLISH_INGEST", "Process")
if ($publishIngest -eq "1") {
    Write-Host "[ops-fusion] Step 7/7: publish_showroom_public_event.ps1 (SHOWROOM_PUBLISH_INGEST=1)"
    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\publish_showroom_public_event.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "publish_showroom_public_event.ps1 failed with exit code $LASTEXITCODE"
    }
} else {
    Write-Host "[ops-fusion] Step 7/7: skipped (set SHOWROOM_PUBLISH_INGEST=1 to POST bundle to public-event ingest)"
}

Write-Host "[ops-fusion] Completed successfully."
