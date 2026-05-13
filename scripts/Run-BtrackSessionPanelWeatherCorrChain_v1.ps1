#Requires -Version 5.1
<#
.SYNOPSIS
  Windows wrapper for `scripts/run_btrack_session_panel_weather_corr_chain_v1.py` (panel → join → correlate).

.DESCRIPTION
  Forwards all arguments to Python. Run from repo root:

    pwsh -File scripts/Run-BtrackSessionPanelWeatherCorrChain_v1.ps1 --date-from 2024-06-12 --date-to 2024-06-14 --calendar-mode all --weather-csv path\to\daily.csv --ohlcv-csv research\market_data\kospi_daily_external_yf.csv --out-dir reports --tag my_run

  See Python script docstring for full options.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
& py (Join-Path $root "scripts\run_btrack_session_panel_weather_corr_chain_v1.py") @args
exit $LASTEXITCODE
