#Requires -Version 5.1
<#
.SYNOPSIS
  O-P28 auto-chain: holdout -> gated per-date shadow -> score shadow -> eval shadow -> optional recommended chain.

.DESCRIPTION
  research_only. Exit 0 when holdout passes and shadow artifacts written.
  Does NOT overwrite prophecy_hit_rate_eval_latest.json unless -PromoteHeadlineEval (not default).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$MinConfidence = 0.18,
    [switch]$PromoteHeadlineEval,
    [switch]$SkipRecommendedChain,
    [switch]$SkipAmsaengBundle
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $py)) { $py = (Get-Command py -ErrorAction Stop).Source }

$perDate180 = Join-Path $WorkspaceRoot "reports\btrack_ensemble_per_date_directions_180d_v1_latest.json"
$perDateGated = Join-Path $WorkspaceRoot "reports\btrack_ensemble_per_date_directions_180d_op28_gated_v1_latest.json"
$scoreShadow = Join-Path $WorkspaceRoot "reports\btrack_prophecy_score_op28_shadow_v1_latest.json"
$evalShadow = Join-Path $WorkspaceRoot "reports\prophecy_hit_rate_eval_op28_shadow_v1_latest.json"
$holdoutOut = Join-Path $WorkspaceRoot "reports\prophecy_headline_confidence_holdout_v1_latest.json"
$btc = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
$kospi = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"

Write-Host "==> O-P28 holdout eval" -ForegroundColor Cyan
& $py scripts/eval_prophecy_headline_confidence_holdout_v1.py --output $holdoutOut
$holdoutCode = [int]$LASTEXITCODE
if ($holdoutCode -ne 0) {
    if ($PromoteHeadlineEval) {
        Write-Host "[HOLDOUT_WARN] exit=$holdoutCode — commander PromoteHeadlineEval overrides holdout gate" -ForegroundColor Yellow
    } else {
        Write-Host "[HOLDOUT_FAIL] exit=$holdoutCode — shadow promotion skipped" -ForegroundColor Yellow
        exit $holdoutCode
    }
}

Write-Host "==> Apply min_direction_confidence gate to per-date 180d" -ForegroundColor Cyan
& $py scripts/apply_btrack_min_conf_to_per_date_directions_v1.py `
    --input $perDate180 `
    --output $perDateGated `
    --min-direction-confidence $MinConfidence
if ($LASTEXITCODE -ne 0) { throw "apply gate failed" }

Write-Host "==> Build shadow score (dual-leg 180d)" -ForegroundColor Cyan
& $py scripts/build_btrack_prophecy_score_from_ohlcv.py `
    --btc-csv $btc `
    --kospi-csv $kospi `
    --per-date-direction-json $perDateGated `
    --recent-trading-days 180 `
    --force-dual-leg-panel `
    --neutral-bps 4.0 `
    --output $scoreShadow
if ($LASTEXITCODE -ne 0) { throw "shadow score build failed" }

Write-Host "==> Eval shadow hit-rate (active-style: skip neutral preds in panel)" -ForegroundColor Cyan
& $py scripts/eval_prophecy_hit_rate_v1.py `
    --run-mode price `
    --score-json $scoreShadow `
    --output $evalShadow
if ($LASTEXITCODE -ne 0) { throw "shadow eval failed" }

if ($PromoteHeadlineEval) {
    Write-Host "==> HEADLINE PROMOTION (commander approved)" -ForegroundColor Yellow
    $perDateCanon180 = Join-Path $WorkspaceRoot "reports\btrack_ensemble_per_date_directions_180d_v1_latest.json"
    $perDateCanonV1 = Join-Path $WorkspaceRoot "reports\btrack_ensemble_per_date_directions_v1_latest.json"
    $scoreHeadline = Join-Path $WorkspaceRoot "reports\btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
    Copy-Item -LiteralPath $perDateGated -Destination $perDateCanon180 -Force
    Copy-Item -LiteralPath $perDateGated -Destination $perDateCanonV1 -Force
    Copy-Item -LiteralPath $scoreShadow -Destination $scoreHeadline -Force
    & $py scripts/promote_op28_headline_kpi_v1.py `
        --score-json $scoreShadow `
        --per-date-json $perDateGated `
        --min-confidence $MinConfidence
    if ($LASTEXITCODE -ne 0) { throw "headline KPI promote failed" }
    Write-Host "  headline: docs\final\artifacts\prophecy_hit_rate_eval_latest.json (ACTIVE KPI)" -ForegroundColor Green
    Write-Host "  per-date: reports\btrack_ensemble_per_date_directions_180d_v1_latest.json" -ForegroundColor Green
    Write-Host "  score:    reports\btrack_prophecy_score_recommended_eval_chain_v1_latest.json" -ForegroundColor Green
}

if (-not $SkipRecommendedChain) {
    Write-Host "==> Recommended eval chain (lens WF / gates)" -ForegroundColor Cyan
    & $py scripts/run_prophecy_btrack_recommended_eval_chain_v1.py `
        --per-date-direction-json $perDateGated `
        --neutral-bps 4.0
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] recommended chain exit=$LASTEXITCODE (non-fatal for O-P28)" -ForegroundColor Yellow
    }
}

if (-not $SkipAmsaengBundle) {
    Write-Host "==> Amsaeng monitoring bundle (soft fail)" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File `
        (Join-Path $WorkspaceRoot "scripts\Run-AmsaengEosaMonitoringBundleTask.ps1") `
        -GovernanceSoftFail
}

Write-Host ""
Write-Host "[OK] O-P28 chain complete" -ForegroundColor Green
Write-Host "  holdout: $holdoutOut"
Write-Host "  gated:   $perDateGated"
Write-Host "  score:   $scoreShadow"
Write-Host "  eval:    $evalShadow"
