# Market-weight grid 0.4–1.0 for index per-date rail ([HYPO])
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..
py scripts/run_agct_market_psych_weight_ablation_v1.py --profile-set market_sweep
exit $LASTEXITCODE
