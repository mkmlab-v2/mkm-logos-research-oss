#Requires -Version 5.1
<#
.SYNOPSIS
  Windows wrapper for web_ops_regime CDP probe (live CDP or portal JSON fallback).

.EXAMPLE
  pwsh -File scripts/Run-WebOpsRegimeCdpProbe_v1.ps1 --from-nebius-json reports/nvidia_nebius_console_setup_latest.json

.EXAMPLE
  pwsh -File scripts/Run-WebOpsRegimeCdpProbe_v1.ps1 --host-filter console.nebius.com
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
& py (Join-Path $root "scripts\run_web_ops_regime_cdp_probe_v1.py") @args
exit $LASTEXITCODE
