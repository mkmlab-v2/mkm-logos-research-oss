#Requires -Version 5.1
<#
.SYNOPSIS
  Backfill Binance fills into cursor_trade_history and rebuild daily execution feature cache.

.DESCRIPTION
  B-track / research_only. Wraps export_binance_fills_to_cursor_trade_history_v1.py then
  build_btrack_fills_daily_feature_cache_v1.py. Requires local bitcoin-trading API credentials.

.PARAMETER Hours
  Lookback window (default 8760 = ~1 year).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-BtrackFillsArchiveBackfill_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-BtrackFillsArchiveBackfill_v1.ps1 -Hours 168 -WhatIfOnly
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$Hours = 8760,
    [switch]$WhatIfOnly,
    [switch]$RunSync
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath $WorkspaceRoot
Set-Location -LiteralPath $root

$export = Join-Path $root "projects\bitcoin-trading\scripts\export_binance_fills_to_cursor_trade_history_v1.py"
$cache = Join-Path $root "scripts\build_btrack_fills_daily_feature_cache_v1.py"
$outDir = Join-Path $root "projects\bitcoin-trading\exports\cursor_trade_history"
$trades = Join-Path $outDir "trades_treatment.json"

Write-Host "==> fills archive backfill hours=$Hours out=$outDir"
if ($WhatIfOnly) {
    Write-Host "[WhatIfOnly] export + cache commands skipped."
    exit 0
}

if (-not (Test-Path -LiteralPath $export)) {
    throw "Missing export script: $export"
}

$exportArgs = @(
    $export,
    "--hours", [string]$Hours,
    "--out-dir", $outDir
)
if ($RunSync) {
    $exportArgs += "--run-sync"
}

& py @exportArgs
if ($LASTEXITCODE -ne 0) {
    throw "export_binance_fills exit $LASTEXITCODE (check API keys / network)"
}

& py $cache --trades-json $trades
if ($LASTEXITCODE -ne 0) {
    throw "build_btrack_fills_daily_feature_cache exit $LASTEXITCODE"
}

$shadowSync = Join-Path $root "scripts\refresh_cursor_trade_shadow_from_treatment_v1.py"
if (Test-Path -LiteralPath $shadowSync) {
    & py $shadowSync
    if ($LASTEXITCODE -ne 0) {
        throw "refresh_cursor_trade_shadow_from_treatment exit $LASTEXITCODE"
    }
}

exit 0
