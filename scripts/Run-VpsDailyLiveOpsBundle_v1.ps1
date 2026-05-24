#Requires -Version 5.1
<#
.SYNOPSIS
  Daily live ops: ensemble v2 risk refresh, VPS crons, export now, GO sync, ops snapshot.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-VpsDailyLiveOpsBundle_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [switch]$SkipEnsembleEval,
    [switch]$SkipCronRegister
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "==> local Fact-Safe + GO" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-FactSafeRiskProfileSyncChain_v1.ps1 -ExitZeroOnNoGo
if ($LASTEXITCODE -ne 0) { throw "FactSafe chain: $LASTEXITCODE" }

if (-not $SkipEnsembleEval) {
    Write-Host "==> ensemble v2 recommended eval (risk inputs; no live order change)" -ForegroundColor Cyan
    py scripts\run_prophecy_btrack_recommended_eval_chain_v1.py --ensemble-v2-lane --neutral-bps 0.8
    if ($LASTEXITCODE -ne 0) { throw "ensemble v2 eval: $LASTEXITCODE" }
    py scripts\refresh_gut_brain_btrack_promotion_status_v1.py
}

if (-not $SkipCronRegister) {
    Write-Host "==> VPS crons" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-VpsBinanceExportCron_v1.ps1 -VpsHost $VpsHost -DestinyRoot $DestinyRoot
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-VpsAroonSignalWatchCron_v1.ps1 -VpsHost $VpsHost -DestinyRoot $DestinyRoot
}

Write-Host "==> VPS export + aroon dispatch probe" -ForegroundColor Cyan
$bt = "$DestinyRoot/projects/bitcoin-trading"
ssh $VpsHost "cd '$bt' && python3 scripts/export_binance_fills_to_cursor_trade_history_v1.py --hours 24 --run-sync && python3 scripts/dispatch_aroon_signal_webhook_v1.py"
if ($LASTEXITCODE -ne 0) { Write-Host "VPS export/dispatch warning exit $LASTEXITCODE" -ForegroundColor Yellow }

Write-Host "==> push risk + GO to VPS" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\apply_prophecy_live_enable_small_v1.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-VpsTradingGoReadinessSync_v1.ps1 -VpsHost $VpsHost -DestinyRoot $DestinyRoot

Write-Host "DONE Run-VpsDailyLiveOpsBundle_v1" -ForegroundColor Green
