#Requires -Version 5.1
<#
.SYNOPSIS
  Windows wrapper for run_weather_synthetic_120d_chain_and_brier_v1.py (forwards all args).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$pyArgs = @($args)
& py -3 (Join-Path $WorkspaceRoot "scripts\run_weather_synthetic_120d_chain_and_brier_v1.py") @pyArgs
exit $LASTEXITCODE
