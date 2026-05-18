#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path) | Split-Path -Parent
py scripts/run_ultra_compression_promotion_sweep_v1.py @args
exit $LASTEXITCODE
