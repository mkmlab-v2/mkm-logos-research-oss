#Requires -Version 5.1
<#
.SYNOPSIS
  Regenerate B-track health bridge pinpoint JSON (never writes Track A active report).

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Run-UltraCompressionHealthBridgePinpoint_v1.ps1
  pwsh -File scripts/Run-UltraCompressionHealthBridgePinpoint_v1.ps1 -DryRun
#>
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$pyArgs = @()
if ($DryRun) { $pyArgs += "--dry-run" }
& py (Join-Path $root "scripts\run_ultra_compression_health_bridge_pinpoint_v1.py") @pyArgs
exit $LASTEXITCODE
