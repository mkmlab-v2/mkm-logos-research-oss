#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly B-track prophecy learning bundle (measurement only; no live auto-promotion).

.DESCRIPTION
  1. Refresh KOSPI/BTC OHLCV CSV if missing
  2. neutral_bps auto-sweep + apply best row (reports/*_recommended*)
  3. Promote sweep score+WF into docs/final/artifacts/*_latest.json (observation SSOT)
  4. Daily eval with walk-forward regen (30 trading days, SkipTrinity)
  5. Evolution watchdog + hit-rate tail append

  OPERATION_MODE_B: does not enable trading or A-track promotion.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipAutoSweep,
    [switch]$SkipHeadlineGatesSweep,
    [switch]$SkipDailyEval,
    [int]$RecentTradingDays = 30
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $root

$btcCsv = Join-Path $root "research\market_data\btc_daily_external_yf.csv"
$kospiCsv = Join-Path $root "research\market_data\kospi_daily_external_yf.csv"

function Ensure-MarketCsv([string]$CsvPath, [string]$FetchRel) {
    if (Test-Path -LiteralPath $CsvPath) { return }
    $fetch = Join-Path $root $FetchRel
    if (-not (Test-Path -LiteralPath $fetch)) {
        throw "Missing fetch script: $fetch"
    }
    Write-Host "==> $FetchRel (missing $($CsvPath | Split-Path -Leaf))"
    & py $fetch
    if ($LASTEXITCODE -ne 0) {
        throw "$FetchRel exit $LASTEXITCODE"
    }
}

Write-Host "=== B-track weekly learning (Mode B / [HYPO]) ===" -ForegroundColor Cyan
Ensure-MarketCsv -CsvPath $kospiCsv -FetchRel "scripts\fetch_kospi_yfinance_csv.py"
Ensure-MarketCsv -CsvPath $btcCsv -FetchRel "scripts\fetch_btc_yfinance_csv.py"

Write-Host "==> check_evolution_auto_apply_allowlist_v1.py (pre-flight)"
& py (Join-Path $root "scripts\check_evolution_auto_apply_allowlist_v1.py") --strict
if ($LASTEXITCODE -ne 0) {
    throw "evolution allowlist pre-flight exit $LASTEXITCODE"
}

if (-not $SkipAutoSweep) {
    Write-Host "==> Run-BtrackRecommendedEvalAutoSweep_v1.ps1"
    & (Join-Path $root "scripts\Run-BtrackRecommendedEvalAutoSweep_v1.ps1") -WorkspaceRoot $root
    if ($LASTEXITCODE -ne 0) {
        throw "auto-sweep exit $LASTEXITCODE"
    }
}

$repScore = Join-Path $root "reports\btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
$repLens = Join-Path $root "reports\prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
$repInst = Join-Path $root "reports\prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json"
$repGates = Join-Path $root "reports\prophecy_promotion_gates_recommended_chain_v1_latest.json"

$artScore = Join-Path $root "docs\final\artifacts\btrack_prophecy_score_latest.json"
$artLens = Join-Path $root "docs\final\artifacts\prophecy_per_date_combo_walkforward_v1_latest.json"
$artInst = Join-Path $root "docs\final\artifacts\prophecy_instrument_combo_walkforward_v1_latest.json"
$artGates = Join-Path $root "docs\final\artifacts\prophecy_promotion_gates_v1_latest.json"
$hypo = Join-Path $root "docs\final\artifacts\btrack_hypothesis_prophecy_latest.json"

foreach ($pair in @(
        @($repScore, $artScore),
        @($repLens, $artLens),
        @($repInst, $artInst)
    )) {
    if (Test-Path -LiteralPath $pair[0]) {
        Copy-Item -LiteralPath $pair[0] -Destination $pair[1] -Force
        Write-Host "promoted: $($pair[0] | Split-Path -Leaf) -> artifacts"
    }
}

if (-not $SkipHeadlineGatesSweep) {
    Write-Host "==> Run-BtrackHeadlineGatesRecommendedSweep_v1.ps1 (min_confidence + score_abs_deadzone)"
    $hgParams = @{ WorkspaceRoot = $root }
    if (Test-Path -LiteralPath $artScore) {
        $hgParams["ScoreJson"] = $artScore
    } elseif (Test-Path -LiteralPath $repScore) {
        $hgParams["ScoreJson"] = $repScore
    }
    & (Join-Path $root "scripts\Run-BtrackHeadlineGatesRecommendedSweep_v1.ps1") @hgParams
    if ($LASTEXITCODE -ne 0) {
        throw "headline gates sweep exit $LASTEXITCODE"
    }
}

if ((Test-Path -LiteralPath $artScore) -and (Test-Path -LiteralPath $hypo)) {
    Write-Host "==> eval_prophecy_promotion_gates_v1.py (artifacts, post-sweep)"
    & py (Join-Path $root "scripts\eval_prophecy_promotion_gates_v1.py") `
        --promotion-track-mode dual `
        --lens-walkforward-json $artLens `
        --instrument-walkforward-json $artInst `
        --score-json $artScore `
        --hypothesis-json $hypo `
        --output $artGates
    if ($LASTEXITCODE -ne 0) {
        throw "eval_prophecy_promotion_gates_v1.py exit $LASTEXITCODE"
    }
}

if (-not $SkipDailyEval) {
    Write-Host "==> run_daily_prophecy_eval_and_report.ps1 (WF regen + $RecentTradingDays days)"
    & (Join-Path $root "scripts\run_daily_prophecy_eval_and_report.ps1") `
        -WorkspaceRoot $root `
        -RecentTradingDays $RecentTradingDays `
        -BtcCsvPath $btcCsv `
        -SkipTrinityEvolution `
        -IncludeShadowPanelEval `
        -ShadowPanelMode walkforward_aggregate
    if ($LASTEXITCODE -ne 0) {
        throw "daily eval exit $LASTEXITCODE"
    }
}

Write-Host "==> check_evolution_auto_apply_allowlist_v1.py"
& py (Join-Path $root "scripts\check_evolution_auto_apply_allowlist_v1.py") --strict
if ($LASTEXITCODE -ne 0) {
    throw "evolution allowlist check exit $LASTEXITCODE"
}

Write-Host "==> check_prophecy_evolution_watchdog_v1.py"
& py (Join-Path $root "scripts\check_prophecy_evolution_watchdog_v1.py") `
    --workspace-root $root
if ($LASTEXITCODE -ne 0) {
    throw "evolution watchdog exit $LASTEXITCODE"
}

Write-Host "==> seed_btrack_effective_adjustments_registry_v1.py"
& py (Join-Path $root "scripts\seed_btrack_effective_adjustments_registry_v1.py")
if ($LASTEXITCODE -ne 0) {
    throw "registry seed exit $LASTEXITCODE"
}

Write-Host "[OK] Weekly B-track learning bundle complete." -ForegroundColor Green
