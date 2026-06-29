# DNA-only / market-psych-only / 0.6-0.4 fusion — 30d+252d price ablation ([HYPO])
param(
    [switch]$RefreshYfinance
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..
$py = 'py'
$args = @('scripts/run_agct_market_psych_weight_ablation_v1.py')
if ($RefreshYfinance) { $args += '--refresh-yfinance' }
& $py @args
exit $LASTEXITCODE
