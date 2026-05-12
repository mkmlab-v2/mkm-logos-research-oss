#Requires -Version 5.1
<#
.SYNOPSIS
  Run one strict-streak cycle for B-track prophecy gates (research-only).

.DESCRIPTION
  Uses the currently validated strict candidate setup:
  - score window: recent-trading-days=30
  - neutral_bps=8
  - per-date walkforward: n_folds=3, include source direction signal + expanded prior features
  - promotion gates: btc_only_crossassist, strict_streak_required=5

  Writes/refreshes:
  - docs/final/artifacts/btrack_prophecy_score_latest.json
  - docs/final/artifacts/prophecy_per_date_combo_walkforward_v1_latest.json
  - docs/final/artifacts/prophecy_hit_rate_eval_latest.json
  - docs/final/artifacts/prophecy_promotion_gates_v1_latest.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$BtcCsv = "",
    [int]$RecentTradingDays = 30,
    [double]$NeutralBps = 8.0,
    [int]$NFolds = 3
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location -LiteralPath $WorkspaceRoot

if ([string]::IsNullOrWhiteSpace($BtcCsv)) {
    $BtcCsv = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
}
if (-not (Test-Path -LiteralPath $BtcCsv)) {
    throw "BTC CSV not found: $BtcCsv"
}

$score = "docs/final/artifacts/btrack_prophecy_score_latest.json"
$wf = "docs/final/artifacts/prophecy_per_date_combo_walkforward_v1_latest.json"
$hit = "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
$gate = "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
$instrumentWf = "docs/final/artifacts/prophecy_instrument_combo_walkforward_v1_latest.json"
$streak = "docs/final/artifacts/prophecy_promotion_strict_streak_legacy_v1.json"

Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py (30d strict candidate)" -ForegroundColor Cyan
py scripts/build_btrack_prophecy_score_from_ohlcv.py `
  --btc-csv $BtcCsv `
  --recent-trading-days $RecentTradingDays `
  --neutral-bps $NeutralBps `
  --output $score
if ($LASTEXITCODE -ne 0) { throw "score builder failed: $LASTEXITCODE" }

Write-Host "==> run_prophecy_per_date_combo_walkforward_v1.py (n_folds=$NFolds)" -ForegroundColor Cyan
py scripts/run_prophecy_per_date_combo_walkforward_v1.py `
  --score-json $score `
  --btc-csv $BtcCsv `
  --target-instrument btc `
  --train-objective accuracy `
  --n-folds $NFolds `
  --include-source-direction-signal `
  --include-expanded-prior-features `
  --output $wf
if ($LASTEXITCODE -ne 0) { throw "per-date WF failed: $LASTEXITCODE" }

Write-Host "==> eval_prophecy_hit_rate_v1.py (price)" -ForegroundColor Cyan
py scripts/eval_prophecy_hit_rate_v1.py `
  --run-mode price `
  --score-json $score `
  --output $hit
if ($LASTEXITCODE -ne 0) { throw "hit-rate eval failed: $LASTEXITCODE" }

Write-Host "==> eval_prophecy_promotion_gates_v1.py (strict streak)" -ForegroundColor Cyan
py scripts/eval_prophecy_promotion_gates_v1.py `
  --lens-walkforward-json $wf `
  --instrument-walkforward-json $instrumentWf `
  --score-json $score `
  --promotion-track-mode btc_only_crossassist `
  --min-mean 0.55 `
  --max-stdev 0.15 `
  --min-beat-bull-frac 0.5 `
  --min-worst-fold 0.4 `
  --strict-streak-required 5 `
  --streak-history-json $streak `
  --output $gate
if ($LASTEXITCODE -ne 0) { throw "promotion gate eval failed: $LASTEXITCODE" }

$g = Get-Content -LiteralPath $gate -Raw | ConvertFrom-Json
Write-Host ("DONE strict={0} streak={1} auto_promote_ready={2}" -f $g.strict_passed, $g.strict_pass_streak, $g.auto_promote_ready) -ForegroundColor Green
