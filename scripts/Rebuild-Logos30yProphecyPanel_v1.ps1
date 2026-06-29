#Requires -Version 5.1
<#
.SYNOPSIS
  Rebuild long KOSPI dual-leg score + sidecar for Logos strict OOS (research_only).

.DESCRIPTION
  1) fetch KOSPI/BTC CSV (--start 2010; BTC needs --end)
  2) ensemble per-date directions (full KOSPI∩BTC intersection)
  3) build btrack_prophecy_score_30y_dual_latest.json
  4) insight sidecar 30y
  5) optional: strict OOS grid sweep + logos_oos_gate_promote

  B-track [HYPO] — not Track A / live trading.

  WARNING: run_prophecy_logos_revalidation_suite_v1.py on a new panel can fail OOS (go=false).
  Golden 252d is preserved via suite/promote guards; maturity SSOT uses prophecy_logos_revalidation_oos_gate_latest.json.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipFetch,
    [switch]$SkipOosSweep,
    [string]$BtcEndDate = "2026-06-05"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) { $py = "python" }

if (-not $SkipFetch) {
    & $py scripts/fetch_kospi_yfinance_csv.py --start 2010-01-01
    if ($LASTEXITCODE -ne 0) { throw "fetch_kospi exit $LASTEXITCODE" }
    & $py scripts/fetch_btc_yfinance_csv.py --start 2010-01-01 --end $BtcEndDate
    if ($LASTEXITCODE -ne 0) { throw "fetch_btc exit $LASTEXITCODE" }
}

& $py -c @"
from pathlib import Path
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows
from scripts.build_btrack_prophecy_score_from_ohlcv import _past_sorted_intersection_dates
k=load_kospi_yf_rows(Path('research/market_data/kospi_daily_external_yf.csv'))
b=load_kospi_yf_rows(Path('research/market_data/btc_daily_external_yf.csv'))
n=len(_past_sorted_intersection_dates(k,b))
print(n)
"@ | Out-String -Stream | ForEach-Object { if ($_ -match '^\d+$') { [int]$_ } } | Select-Object -Last 1 | Tee-Object -Variable nVal
$n = [int]$nVal
if ($n -lt 252) { throw "intersection days $n < 252" }

& $py scripts/build_btrack_ensemble_per_date_directions_v1.py `
    --recent-trading-days $n `
    --target-instrument kospi `
    --output reports/btrack_ensemble_per_date_directions_30y_v1.json
if ($LASTEXITCODE -ne 0) { throw "ensemble exit $LASTEXITCODE" }

& $py scripts/build_btrack_prophecy_score_from_ohlcv.py `
    --recent-trading-days $n `
    --force-dual-leg-panel `
    --kospi-csv research/market_data/kospi_daily_external_yf.csv `
    --btc-csv research/market_data/btc_daily_external_yf.csv `
    --hypothesis-json docs/final/artifacts/btrack_hypothesis_prophecy_latest.json `
    --per-date-direction-json reports/btrack_ensemble_per_date_directions_30y_v1.json `
    --output docs/final/artifacts/btrack_prophecy_score_30y_dual_latest.json
if ($LASTEXITCODE -ne 0) { throw "build_score exit $LASTEXITCODE" }

& $py scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py `
    --score-json docs/final/artifacts/btrack_prophecy_score_30y_dual_latest.json `
    --out docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_latest.json
if ($LASTEXITCODE -ne 0) { throw "sidecar exit $LASTEXITCODE" }

if (-not $SkipOosSweep) {
    & $py scripts/run_logos_strict_oos_grid_sweep_v1.py --promote-if-better --target-instrument kospi `
        --lookbacks 14,21,28,63 --neutrals 0.15,0.2,0.25,0.3,0.5
    if ($LASTEXITCODE -ne 0) { throw "oos_sweep exit $LASTEXITCODE" }
    & $py scripts/logos_oos_gate_promote_v1.py
    if ($LASTEXITCODE -ne 0) { throw "oos_promote exit $LASTEXITCODE" }
}

Write-Host "[OK] Rebuild-Logos30yProphecyPanel_v1 intersection_days=$n" -ForegroundColor Green
