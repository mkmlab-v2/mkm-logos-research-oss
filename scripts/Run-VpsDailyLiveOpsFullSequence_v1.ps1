#Requires -Version 5.1
<#
.SYNOPSIS
  Recommended ops sequence: bundle -> rollback check -> logs -> register task -> VPS script sync.

.EXAMPLE
  powershell -File scripts\Run-VpsDailyLiveOpsFullSequence_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipBundle,
    [switch]$SkipRegisterTask,
    [switch]$RegisterTaskOnly
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ($RegisterTaskOnly) {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-VpsDailyLiveOpsWindowsTask_v1.ps1
    exit $LASTEXITCODE
}

if (-not $SkipBundle) {
    Write-Host "=== [1/6] Daily live ops bundle (ensemble v2) ===" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-VpsDailyLiveOpsBundle_v1.ps1 -SkipCronRegister
    if ($LASTEXITCODE -ne 0) { throw "bundle exit $LASTEXITCODE" }
}

Write-Host "=== [2/6] Rollback check (24h PnL vs 2%) ===" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ProphecyLiveRollbackCheck_v1.ps1
if ($LASTEXITCODE -eq 2) {
    Write-Host "WARN: rollback breach detected (read-only; use -ApplyDisable to disable live on VPS)" -ForegroundColor Yellow
}

Write-Host "=== [3/6] VPS PM2 + logs tail ===" -ForegroundColor Cyan
ssh vps-mkmlife "pm2 describe bitcoin-live-small-24h 2>/dev/null | grep -E 'status|restarts|uptime' | head -5 || echo pm2_app_missing"
ssh vps-mkmlife "tail -8 /var/log/aroon_signal_webhook.log 2>/dev/null || echo no_aroon_log"
ssh vps-mkmlife "tail -5 /var/log/bitcoin_export_then_cursor_trade_history.log 2>/dev/null || echo no_export_log"

Write-Host "=== [4/6] Webhook sync verify ===" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-SyncVpsOpsAlarmWebhook_v1.ps1 -SkipDispatchTest

Write-Host "=== [5/6] Register Windows daily task ===" -ForegroundColor Cyan
if (-not $SkipRegisterTask) {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-VpsDailyLiveOpsWindowsTask_v1.ps1
}

Write-Host "=== [6/6] VPS script sync ===" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-VpsLiveOpsScripts_v1.ps1

Write-Host "DONE Run-VpsDailyLiveOpsFullSequence_v1" -ForegroundColor Green
