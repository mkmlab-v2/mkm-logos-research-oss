#Requires -Version 5.1
<#
.SYNOPSIS
  Register VPS cron: Binance fills export + cursor_trade_history 24h sync (every 30m).

.PARAMETER DestinyRoot
  Monorepo root on VPS (default /opt/mkm-destiny-ai-41e38ec6).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-VpsBinanceExportCron_v1.ps1
#>
param(
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [string]$Schedule = "*/30 * * * *",
    [int]$ExportHours = 24
)

$ErrorActionPreference = "Stop"
$sh = Join-Path $PSScriptRoot "deploy\linux\register_vps_live_ops_cron_v1.sh"
if (-not (Test-Path -LiteralPath $sh)) { throw "Missing $sh" }
scp $sh "${VpsHost}:/tmp/register_vps_live_ops_cron_v1.sh"
ssh $VpsHost "sed -i 's/\r$//' /tmp/register_vps_live_ops_cron_v1.sh && DESTINY_ROOT='$DestinyRoot' EXPORT_SCHEDULE='$Schedule' bash /tmp/register_vps_live_ops_cron_v1.sh"
if ($LASTEXITCODE -ne 0) { throw "cron register failed: $LASTEXITCODE" }
Write-Host "OK VPS live ops crons (export $Schedule)" -ForegroundColor Green
