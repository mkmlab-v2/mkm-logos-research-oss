#Requires -Version 5.1
<#
.SYNOPSIS
  Refresh 24h trade window (local + optional VPS export) then check rollback policy.

.PARAMETER ApplyDisable
  On breach: set ENABLE_TRADING=false on VPS .env and restart bitcoin-live-small-24h (high risk; explicit).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [string]$Pm2App = "bitcoin-live-small-24h",
    [double]$ReferenceUsdt = 0,
    [switch]$SkipVpsExport,
    [switch]$StrictExit,
    [switch]$ApplyDisable
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if (-not $SkipVpsExport) {
    Write-Host "==> VPS export 24h (for rollback PnL)" -ForegroundColor Cyan
    $bt = "$DestinyRoot/projects/bitcoin-trading"
    ssh $VpsHost "cd $bt && python3 scripts/export_binance_fills_to_cursor_trade_history_v1.py --hours 24 --run-sync --sync-hours 24"
    if ($LASTEXITCODE -ne 0) { Write-Host "WARN: VPS export exit $LASTEXITCODE" -ForegroundColor Yellow }
    $remoteWin = "$bt/exports/cursor_trade_history/cursor_trade_history_latest_24h.json"
    $localWin = "projects\bitcoin-trading\exports\cursor_trade_history\cursor_trade_history_latest_24h.json"
    scp "${VpsHost}:${remoteWin}" $localWin
}

$pyArgs = @("scripts\check_prophecy_live_rollback_v1.py")
if ($ReferenceUsdt -gt 0) { $pyArgs += @("--reference-usdt", [string]$ReferenceUsdt) }
if ($StrictExit) { $pyArgs += "--strict-exit" }
py @pyArgs
$checkExit = $LASTEXITCODE

$report = Get-Content "reports\prophecy_live_rollback_check_v1_latest.json" -Raw | ConvertFrom-Json
if ($report.rollback_triggered -and $ApplyDisable) {
    Write-Host "==> ApplyDisable: ENABLE_TRADING=false on VPS + pm2 restart $Pm2App" -ForegroundColor Red
    $patch = "cd $DestinyRoot && touch .env && (grep -v '^ENABLE_TRADING=' .env > .env.tmp || true) && echo ENABLE_TRADING=false >> .env.tmp && mv .env.tmp .env && pm2 restart $Pm2App --update-env"
    ssh $VpsHost $patch
}
exit $checkExit
