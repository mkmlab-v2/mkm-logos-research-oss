#Requires -Version 5.1
<#
.SYNOPSIS
  Register VPS cron: Aroon signal change webhook (every 5 minutes).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-VpsAroonSignalWatchCron_v1.ps1
#>
param(
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [string]$Schedule = "*/5 * * * *"
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "Register-VpsBinanceExportCron_v1.ps1") -VpsHost $VpsHost -DestinyRoot $DestinyRoot -Schedule "*/30 * * * *"
Write-Host "OK (combined register_vps_live_ops_cron_v1.sh includes aroon $Schedule)" -ForegroundColor Green
