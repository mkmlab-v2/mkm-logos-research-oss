#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path) | Split-Path -Parent
py scripts/apply_multilens_ultra_compression_track_a_promotion_v1.py @args
exit $LASTEXITCODE
