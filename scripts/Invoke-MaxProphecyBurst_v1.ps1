#Requires -Version 5.1
<#
.SYNOPSIS
  B-track prophecy burst: optional yfinance CSV refresh, general registry JSON, optional daily chain, OHLCV score + hit-rate eval.

.DESCRIPTION
  Fact-Lock aligned entry points only.
  - generate_general_prophecy_v1.py: validate/merge default fixtures + refresh generated_at_utc (no --force-update).
  - eval_prophecy_hit_rate_v1.py --run-mode price requires --score-json (build_btrack_prophecy_score_from_ohlcv output).
  - Default score: docs/final/artifacts/btrack_prophecy_score_latest.json
  - Default hit-rate report: docs/final/artifacts/prophecy_hit_rate_eval_latest.json
  - Default BTC CSV (when present or after -FetchMarketData): research/market_data/btc_daily_external_yf.csv
  When --recent-trading-days N is greater than 1, the Python builder uses the last N KOSPI trading dates from the CSV (batch mode); --eval-date is still required by the CLI but the batch loop selects dates from OHLCV (see build_btrack_prophecy_score_from_ohlcv.py).

.PARAMETER Profile
  Lite: skip market CSV fetch inside daily chain, skip in-chain hit-rate, skip Gemini contemplation, skip panel 24h alerts.
  Full: daily chain may refresh market data unless -SkipMarketDataRefreshInChain is set; still skips paid Gemini unless -AllowGeminiContemplation.

.PARAMETER FetchMarketData
  Run fetch_kospi_yfinance_csv.py + fetch_btc_yfinance_csv.py before OHLCV scoring (network; requires pandas+yfinance).

.PARAMETER BtcCsv
  Explicit path for --btc-csv on build_btrack_prophecy_score_from_ohlcv.py. When empty, uses default BTC CSV path if the file exists.

.PARAMETER OhlcvEvalDate
  Trading date for OHLCV score row. Default: yesterday (local calendar).

.PARAMETER SkipMarketDataRefreshInChain
  When Profile=Full, pass -SkipMarketDataRefresh into the daily chain (use with -FetchMarketData to avoid double fetch).

.PARAMETER RecentTradingDays
  Passed to build_btrack_prophecy_score_from_ohlcv.py --recent-trading-days. N>1 emits one row per leg per past KOSPI trading day (last N from CSV), enabling walkforward scripts that need 2+ distinct eval_dates. Default 5. Use 1 for a single-day score only (WF refresh may WARN).

.PARAMETER SkipWalkforwardRefresh
  When set, do not re-run run_prophecy_per_date_combo_walkforward_v1 / instrument combo after the score build (default: run when RecentTradingDays >= 2).
#>
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [ValidateSet("Lite", "Full")]
    [string]$Profile = "Lite",
    [string]$OhlcvEvalDate = "",
    [string]$BtcCsv = "",
    [int]$RecentTradingDays = 5,
    [switch]$FetchMarketData,
    [switch]$StubGeneralProphecyForecasts,
    [switch]$SkipDailyChain,
    [switch]$AllowGeminiContemplation,
    [switch]$SkipMarketDataRefreshInChain,
    [switch]$SkipWalkforwardRefresh
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

if (-not $OhlcvEvalDate) {
    $OhlcvEvalDate = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
}
if ($RecentTradingDays -lt 1) {
    throw "RecentTradingDays must be >= 1 (got $RecentTradingDays)."
}

$defaultBtc = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
$scoreJson = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_latest.json"
$hitRateOut = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_latest.json"
$generalOut = Join-Path $WorkspaceRoot "docs\final\artifacts\general_prophecy_latest.json"

function Write-Step([string]$msg) {
    Write-Host "[MaxProphecyBurst] $msg" -ForegroundColor Cyan
}

Write-Step "Workspace=$WorkspaceRoot Profile=$Profile OhlcvEvalDate=$OhlcvEvalDate RecentTradingDays=$RecentTradingDays FetchMarketData=$FetchMarketData"

if ($FetchMarketData) {
    Write-Step "0 fetch_kospi_yfinance_csv.py + fetch_btc_yfinance_csv.py (yfinance)"
    & py scripts/fetch_kospi_yfinance_csv.py
    if ($LASTEXITCODE -ne 0) { throw "fetch_kospi_yfinance_csv.py exit $LASTEXITCODE" }
    & py scripts/fetch_btc_yfinance_csv.py
    if ($LASTEXITCODE -ne 0) { throw "fetch_btc_yfinance_csv.py exit $LASTEXITCODE" }
}

# 1) General prophecy registry pass-through
Write-Step "1/4 generate_general_prophecy_v1.py -> $generalOut"
$genArgs = @("scripts/generate_general_prophecy_v1.py")
if ($StubGeneralProphecyForecasts) { $genArgs += "--stub-forecasts" }
& py @genArgs
if ($LASTEXITCODE -ne 0) { throw "generate_general_prophecy_v1.py exit $LASTEXITCODE" }

# 2) Daily B-track hypothesis chain (optional)
if (-not $SkipDailyChain) {
    Write-Step "2/4 run_btrack_daily_hypothesis_chain.ps1"
    $chain = Join-Path $WorkspaceRoot "scripts\run_btrack_daily_hypothesis_chain.ps1"
    if ($Profile -eq "Lite") {
        $chainArgs = @{
            WorkspaceRoot                    = $WorkspaceRoot
            SkipMarketDataRefresh            = $true
            SkipHitRate                      = $true
            SkipProphecyContemplationGemini  = $true
            SkipPanel24hAlertsCheck          = $true
        }
        if ($AllowGeminiContemplation) { $chainArgs.Remove("SkipProphecyContemplationGemini") }
        & $chain @chainArgs
    }
    else {
        $chainArgs = @{ WorkspaceRoot = $WorkspaceRoot; SkipProphecyContemplationGemini = (-not $AllowGeminiContemplation) }
        if ($FetchMarketData -or $SkipMarketDataRefreshInChain) {
            $chainArgs["SkipMarketDataRefresh"] = $true
        }
        & $chain @chainArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "run_btrack_daily_hypothesis_chain.ps1 exit $LASTEXITCODE" }
}
else {
    Write-Step "2/4 SKIP daily chain (-SkipDailyChain)"
}

$resolvedBtc = $BtcCsv
if (-not $resolvedBtc) {
    if (Test-Path -LiteralPath $defaultBtc) { $resolvedBtc = $defaultBtc }
}

# 3) OHLCV score + eval
Write-Step "3/4 build_btrack_prophecy_score_from_ohlcv.py (eval-date=$OhlcvEvalDate recent-trading-days=$RecentTradingDays) -> $scoreJson"
$buildArgs = @(
    "scripts/build_btrack_prophecy_score_from_ohlcv.py",
    "--eval-date", $OhlcvEvalDate,
    "--recent-trading-days", "$RecentTradingDays"
)
if ($resolvedBtc) {
    $buildArgs += "--btc-csv", $resolvedBtc
    Write-Step "Using --btc-csv $resolvedBtc"
}
else {
    Write-Host "[MaxProphecyBurst] WARN: no BTC CSV resolved; score rows may be empty for BTC hypothesis." -ForegroundColor Yellow
}

& py @buildArgs
if ($LASTEXITCODE -ne 0) { throw "build_btrack_prophecy_score_from_ohlcv.py exit $LASTEXITCODE" }

# 3b) Re-run walkforward on the freshly written score (chain step 2 ran WF before this score existed)
if ($RecentTradingDays -ge 2 -and -not $SkipWalkforwardRefresh) {
    Write-Step "3b/4 walkforward refresh (per-date + instrument combo) on $scoreJson"
    & py scripts/run_prophecy_per_date_combo_walkforward_v1.py --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: run_prophecy_per_date_combo_walkforward_v1.py exit $LASTEXITCODE" -ForegroundColor Yellow
    }
    & py scripts/run_prophecy_instrument_combo_walkforward_v1.py --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: run_prophecy_instrument_combo_walkforward_v1.py exit $LASTEXITCODE" -ForegroundColor Yellow
    }
}

Write-Step "4/4 eval_prophecy_hit_rate_v1.py --run-mode price --score-json -> $hitRateOut"
& py scripts/eval_prophecy_hit_rate_v1.py --run-mode price --score-json $scoreJson --output $hitRateOut
if ($LASTEXITCODE -ne 0) { throw "eval_prophecy_hit_rate_v1.py exit $LASTEXITCODE" }

Write-Host "[MaxProphecyBurst] DONE. Key outputs:" -ForegroundColor Green
Write-Host "  - $generalOut"
Write-Host "  - $scoreJson"
Write-Host "  - $hitRateOut"
if (-not $SkipDailyChain) {
    Write-Host "  - docs/final/artifacts/btrack_hypothesis_prophecy_latest.json (if chain wrote)"
}
