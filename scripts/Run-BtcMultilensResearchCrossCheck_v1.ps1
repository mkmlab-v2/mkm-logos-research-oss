# BTC multilens cross-check bundle [HYPO][research_only]
param(
    [switch]$SkipHorizon,
    [switch]$SkipComboWalkforward
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$fetchEndKst = (Get-Date).AddDays(1).ToString('yyyy-MM-dd')
$btcDateTo = (Get-Date).ToString('yyyy-MM-dd')
$parityEnd = (Get-Date).AddDays(-1).ToString('yyyy-MM-dd')
if ($parityEnd -lt '2025-11-01') { $parityEnd = '2026-05-30' }

Write-Host "[1/6] BTC OHLCV extend 2010+ (end=$fetchEndKst)"
py scripts/fetch_btc_yfinance_csv.py --merge --start 2010-01-01 --end $fetchEndKst
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/6] BTC multilens blend full window (to=$btcDateTo)"
py scripts/run_btc_multilens_blend_backtest_v1.py --date-from 2010-01-01 --date-to $btcDateTo
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/6] BTC multilens blend 140d parity window (to=$parityEnd)"
py scripts/run_btc_multilens_blend_backtest_v1.py --date-from 2025-11-01 --date-to $parityEnd --output reports/btc_multilens_blend_backtest_140d_latest.json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '[4/6] BTC multilens walk-forward'
py scripts/run_btc_multilens_walkforward_backtest_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipHorizon) {
    Write-Host '[5/6] Three-lens horizon v2 both'
    py scripts/run_three_lens_horizon_empirical_eval_v2.py --instrument both --date-from 2026-01-01 --date-to 2026-04-30
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host '[5/6] Skip horizon v2'
}

if (-not $SkipComboWalkforward) {
    Write-Host '[6/6] Instrument combo walk-forward (dual-leg panel prereq)'
    py scripts/build_btrack_prophecy_score_from_ohlcv.py `
        --recent-trading-days 90 `
        --force-dual-leg-panel `
        --btc-csv research/market_data/btc_daily_external_yf.csv
    if ($LASTEXITCODE -ne 0) { Write-Warning 'dual-leg panel build failed' }
    py scripts/run_prophecy_instrument_combo_walkforward_v1.py
    if ($LASTEXITCODE -ne 0) { Write-Warning 'instrument combo WF skipped (data prereq)' }
} else {
    Write-Host '[6/6] Skip instrument combo WF'
}

py scripts/build_btc_multilens_cross_check_summary_v1.py
exit $LASTEXITCODE
