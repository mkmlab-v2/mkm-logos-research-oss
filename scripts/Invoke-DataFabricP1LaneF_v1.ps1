# DF-P1-05 Lane F: unified asset registry build + pytest (+ optional P1 chain re-verify)
param(
    [switch]$SkipP1ChainVerify
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== DF-P1-05 unified registry build ==" -ForegroundColor Cyan
py scripts/mkm_unified_asset_registry_v1.py build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== DF-P1-05 pytest ==" -ForegroundColor Cyan
py -m pytest tests/test_mkm_unified_asset_registry_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipP1ChainVerify) {
    Write-Host "== DF-P1-01~03 chain re-verify ==" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-DataFabricP1Parallel_v1.ps1 -SkipPytest
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

py scripts/bootstrap_data_fabric_module_registry_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DF-P1-05 Lane F OK" -ForegroundColor Green
exit 0
