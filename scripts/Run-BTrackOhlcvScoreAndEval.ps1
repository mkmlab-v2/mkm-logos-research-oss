#Requires -Version 5.1
<#
.SYNOPSIS
  OHLCV 기반 btrack_prophecy_score_latest.json 생성 후 price 모드 적중률 eval까지 한 번에 실행합니다.

.DESCRIPTION
  Fact-Lock: scripts/build_btrack_prophecy_score_from_ohlcv.py -> eval_prophecy_hit_rate_v1 --run-mode price
  KOSPI SSOT: research/market_data/kospi_daily_external_yf.csv
  BTC: 기본으로 research/market_data/btc_daily_external_yf.csv 가 있으면 --btc-csv 로 전달(multi 가설 시 두 레그).

.PARAMETER RecentTradingDays
  기본 5. 1이면 단일 평가일 행만.

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Run-BTrackOhlcvScoreAndEval.ps1
  pwsh -File scripts/Run-BTrackOhlcvScoreAndEval.ps1 -RecentTradingDays 30
#>
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [int]$RecentTradingDays = 5,
    [string]$BtcCsv = "",
    [switch]$SkipEval
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$kospiCsv = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"
if (-not (Test-Path -LiteralPath $kospiCsv)) {
    throw "Missing KOSPI CSV (required): $kospiCsv"
}

$btcDefault = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
$btcResolved = if (-not [string]::IsNullOrWhiteSpace($BtcCsv)) {
    if (-not (Test-Path -LiteralPath $BtcCsv)) {
        throw "BTC CSV not found: $BtcCsv"
    }
    $BtcCsv
}
elseif (Test-Path -LiteralPath $btcDefault) {
    $btcDefault
}
else {
    ""
}

if (-not $btcResolved) {
    Write-Host "WARN: No BTC CSV; build runs KOSPI-only unless hypothesis instrument is btc-only." -ForegroundColor Yellow
}

$buildArgs = @(
    "scripts\build_btrack_prophecy_score_from_ohlcv.py",
    "--eval-date", "auto"
)
if ($RecentTradingDays -gt 1) {
    $buildArgs += @("--recent-trading-days", "$RecentTradingDays")
}
if ($btcResolved) {
    $buildArgs += @("--btc-csv", $btcResolved)
}

Write-Host "==> py $($buildArgs -join ' ')" -ForegroundColor Cyan
& py @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "build_btrack_prophecy_score_from_ohlcv.py exit $LASTEXITCODE"
}

if (-not $SkipEval) {
    $scoreJson = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_latest.json"
    Write-Host "==> eval_prophecy_hit_rate_v1.py --run-mode price" -ForegroundColor Cyan
    & py "scripts\eval_prophecy_hit_rate_v1.py" "--run-mode" "price" "--score-json" $scoreJson
    if ($LASTEXITCODE -ne 0) {
        throw "eval_prophecy_hit_rate_v1.py exit $LASTEXITCODE"
    }
}

Write-Host "[OK] Done. Score: docs/final/artifacts/btrack_prophecy_score_latest.json" -ForegroundColor Green
if (-not $SkipEval) {
    Write-Host "[OK] Eval:    docs/final/artifacts/prophecy_hit_rate_eval_latest.json" -ForegroundColor Green
}
