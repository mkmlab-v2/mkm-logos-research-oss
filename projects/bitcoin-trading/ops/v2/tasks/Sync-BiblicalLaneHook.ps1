# Sync workspace biblical single-lane gate outputs into bitcoin-trading memory hook (BTCUSDT).
# Run from repo root:  powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/v2/tasks/Sync-BiblicalLaneHook.ps1
# Or: full stability chain + hook:  scripts/run_kospi_biblical_single_lane_stability_check.ps1 -SyncBitcoinTradingHook

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$btRoot = (Get-Item -LiteralPath (Join-Path $here "..\..\..")).FullName
$workspaceRoot = (Get-Item -LiteralPath (Join-Path $btRoot "..\..")).FullName

Set-Location -LiteralPath $workspaceRoot
& py "scripts/sync_biblical_lane_hook_to_bitcoin_trading.py" @args
exit $LASTEXITCODE
