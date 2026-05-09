#Requires -Version 5.1
<#
.SYNOPSIS
  BTC-first ensemble weight profiles × OHLCV → price hit-rate bundle report (B-track).

.DESCRIPTION
  Runs scripts/run_btc_weight_hit_rate_bundle_v1.py:
    fetch (optional) → per-profile hypothesis → build_btrack_prophecy_score_from_ohlcv → eval_prophecy_hit_rate (price).
  Default output: reports/btrack_btc_weight_hit_rate_bundle_latest.json
  Does not apply weights unless -ApplyWinner is passed (updates docs/final/artifacts/btrack_lens_ensemble_v1.json).

.EXAMPLE
  pwsh -File scripts/Run-BtcWeightWeeklyHitRateBundle_v1.ps1

.EXAMPLE
  pwsh -File scripts/Run-BtcWeightWeeklyHitRateBundle_v1.ps1 -RefreshMarketData -RecentTradingDays 30 -ApplyWinner
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [switch]$RefreshMarketData,
  [int]$RecentTradingDays = 30,
  [int]$MinEvalRows = 5,
  [string]$Profiles = "btc_65,btc_70,btc_80",
  [switch]$ApplyWinner,
  [switch]$DryRun
)
$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$argsList = @(
  "scripts/run_btc_weight_hit_rate_bundle_v1.py",
  "--recent-trading-days", "$RecentTradingDays",
  "--min-eval-rows", "$MinEvalRows",
  "--profiles", $Profiles
)
if ($RefreshMarketData) { $argsList += "--refresh-market-data" }
if ($ApplyWinner) { $argsList += "--apply-winner" }
if ($DryRun) { $argsList += "--dry-run" }

& py @argsList
exit $LASTEXITCODE
