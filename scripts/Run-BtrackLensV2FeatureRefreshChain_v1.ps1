# B-track V2 bundle refresh + per-date rebuild + strict recommended eval (research_only).
param(
    [int]$RecentTradingDays = 180,
    [double]$NeutralBps = 0.4,
    [int]$PriceLookbackDays = 5,
    [switch]$SkipBundle
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
$argsList = @(
    '-u', (Join-Path $root 'scripts\run_btrack_lens_v2_feature_refresh_chain_v1.py'),
    '--recent-trading-days', "$RecentTradingDays",
    '--neutral-bps', "$NeutralBps",
    '--price-lookback-days', "$PriceLookbackDays"
)
if ($SkipBundle) { $argsList += '--skip-bundle' }
& $py @argsList
exit $LASTEXITCODE
