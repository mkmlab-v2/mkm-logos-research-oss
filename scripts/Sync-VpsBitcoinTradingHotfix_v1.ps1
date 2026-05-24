#Requires -Version 5.1
<#
.SYNOPSIS
  Hotfix: scp selected bitcoin-trading paths local → VPS destiny (when git pull/bundle is not used).

.PARAMETER WhatIfOnly
  List files only; no scp.

.PARAMETER IncludeFuturesEngine
  Sync entire projects/bitcoin-trading/src/futures_engine tree.
#>
param(
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$WhatIfOnly,
    [switch]$IncludeFuturesEngine
)

$ErrorActionPreference = "Stop"
$btLocal = Join-Path $WorkspaceRoot "projects\bitcoin-trading"
$btRemote = "$DestinyRoot/projects/bitcoin-trading"

$files = @(
    "src\api\binance_client.py"
)
if ($IncludeFuturesEngine) {
    $fe = Join-Path $btLocal "src\futures_engine"
    Get-ChildItem -Path $fe -Recurse -Filter "*.py" | ForEach-Object {
        $rel = $_.FullName.Substring($btLocal.Length + 1) -replace '\\', '/'
        $files += @($rel -replace '/', '\')
    }
}
$files = $files | Select-Object -Unique

foreach ($rel in $files) {
    $src = Join-Path $btLocal $rel
    if (-not (Test-Path -LiteralPath $src)) {
        Write-Warning "SKIP missing $rel"
        continue
    }
    $remoteRel = ($rel -replace '\\', '/')
    $dst = "${VpsHost}:${btRemote}/${remoteRel}"
    if ($WhatIfOnly) {
        Write-Host "[WHATIF] scp $src -> $dst"
    } else {
        $remoteDir = Split-Path -Parent $remoteRel
        ssh $VpsHost "mkdir -p '$btRemote/$remoteDir'"
        scp $src $dst
        Write-Host "scp OK $rel" -ForegroundColor DarkGray
    }
}
Write-Host "DONE Sync-VpsBitcoinTradingHotfix_v1 (WhatIf=$WhatIfOnly)" -ForegroundColor Green
