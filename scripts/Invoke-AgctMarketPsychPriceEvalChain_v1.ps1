# AGCT DNA + KOSPI market psych -> 30d price hit-rate eval (B-track).
param(
  [int]$EvalDays = 30,
  [int]$PsychDays = 60,
  [switch]$SkipYFinance
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$pyArgs = @(
  "scripts/run_agct_market_psych_price_eval_chain_v1.py",
  "--eval-days", "$EvalDays",
  "--psych-days", "$PsychDays"
)
if ($SkipYFinance) { $pyArgs += "--skip-yfinance" }

py @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
