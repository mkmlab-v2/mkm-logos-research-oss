#Requires -Version 5.1
<#
.SYNOPSIS
  Send one test Aroon-style webhook POST from VPS (does not place orders).

.EXAMPLE
  powershell -File scripts\Invoke-VpsAroonWebhookSmoke_v1.ps1
#>
param(
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$pyLocal = Join-Path $repoRoot "scripts\_vps_aroon_webhook_smoke_v1.py"
scp $pyLocal "${VpsHost}:/tmp/_vps_aroon_webhook_smoke_v1.py"
if ($LASTEXITCODE -ne 0) { throw "scp smoke script failed" }
$cmd = "cd $DestinyRoot && set -a && . ./.env && set +a && python3 /tmp/_vps_aroon_webhook_smoke_v1.py && rm -f /tmp/_vps_aroon_webhook_smoke_v1.py"
ssh $VpsHost $cmd
