# Fusion bundle: manuscript fabric v2 + PoC ref + pytest (no core corpus mutation)
param(
    [switch]$SkipExtendWirePoc,
    [switch]$SkipP2Parallel,
    [switch]$SkipRegistry
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failed = @()

Write-Host "== CM-FABRIC v2 chain ==" -ForegroundColor Cyan
$chainArgs = @("py", "scripts/run_logos_canon_manuscript_fabric_v2_chain_v1.py")
if (-not $SkipExtendWirePoc) {
    $chainArgs += "--extend-wire-poc"
}
& $chainArgs[0] $chainArgs[1..($chainArgs.Length - 1)]
if ($LASTEXITCODE -ne 0) { $failed += "fabric-v2-chain" }

Write-Host "== CM-FABRIC v2 pytest ==" -ForegroundColor Cyan
py -m pytest tests/test_logos_canon_manuscript_fabric_v2.py -q
if ($LASTEXITCODE -ne 0) { $failed += "fabric-v2-pytest" }

if (-not $SkipRegistry) {
    Write-Host "== unified registry (4 lanes incl. manuscript_fabric_v2) ==" -ForegroundColor Cyan
    py scripts/mkm_unified_asset_registry_v1.py build
    if ($LASTEXITCODE -ne 0) { $failed += "unified-registry" }
    py scripts/bootstrap_data_fabric_module_registry_v1.py
}

if (-not $SkipP2Parallel) {
    Write-Host "== P2 parallel (MS readiness + atom anchor) ==" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-DataFabricP2Parallel_v1.ps1
    if ($LASTEXITCODE -ne 0) { $failed += "p2-parallel" }
}

if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "Data Fabric fusion OK" -ForegroundColor Green
exit 0
