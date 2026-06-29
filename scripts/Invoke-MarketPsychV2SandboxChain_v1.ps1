# Market psych v2 sandbox: build CSV -> map -> per-date -> v1/v2 ablation ([HYPO])
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..
py scripts/build_market_psychology_kospi_from_yfinance_v2.py --days 400
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/map_market_psych_to_sasang_axis_v2.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/build_btrack_per_date_directions_market_psych_v2.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/run_market_sasang_lens_from_market_psych_v2_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/run_market_psych_v1_vs_v2_price_ablation_v1.py --skip-yfinance
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/sweep_market_psych_manifest_holdout_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/run_market_psych_manifest_candidate_price_validation_v1.py --skip-yfinance
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/build_session_myeongni_vs_agct_market_psych_comparison_v1.py
exit $LASTEXITCODE
