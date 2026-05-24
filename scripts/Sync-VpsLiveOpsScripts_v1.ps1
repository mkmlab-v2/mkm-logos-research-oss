#Requires -Version 5.1
<#
.SYNOPSIS
  scp live-ops scripts to VPS (when git pull is not enough).
#>
param(
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$bt = "$DestinyRoot/projects/bitcoin-trading"
$files = @(
    @{ Local = "projects\bitcoin-trading\scripts\dispatch_aroon_signal_webhook_v1.py"; Remote = "$bt/scripts/dispatch_aroon_signal_webhook_v1.py" },
    @{ Local = "projects\bitcoin-trading\scripts\sync_cursor_trade_history_latest_24h.py"; Remote = "$bt/scripts/sync_cursor_trade_history_latest_24h.py" },
    @{ Local = "projects\bitcoin-trading\scripts\export_binance_fills_to_cursor_trade_history_v1.py"; Remote = "$bt/scripts/export_binance_fills_to_cursor_trade_history_v1.py" }
)
foreach ($f in $files) {
    $src = Join-Path $WorkspaceRoot $f.Local
    if (-not (Test-Path -LiteralPath $src)) { throw "Missing $src" }
    scp $src "${VpsHost}:$($f.Remote)"
    Write-Host "scp OK $($f.Local)" -ForegroundColor DarkGray
}
Write-Host "DONE Sync-VpsLiveOpsScripts_v1" -ForegroundColor Green
