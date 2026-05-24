# P2+ next: graph 3k roadmap + DF-P2-03 regime highlight + registry
param(
    [int]$TargetNodes = 3000,
    [switch]$SkipGraphRoadmap,
    [switch]$SkipRegimeHighlight,
    [switch]$SkipRegistry
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failed = @()

if (-not $SkipGraphRoadmap) {
    Write-Host "== Graph roadmap -> $TargetNodes ==" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-DataFabricGraphExpandRoadmap_v1.ps1 -TargetNodes $TargetNodes
    if ($LASTEXITCODE -ne 0) { $failed += "graph-roadmap" }
}

if (-not $SkipRegimeHighlight) {
    Write-Host "== DF-P2-03 regime highlight ==" -ForegroundColor Cyan
    py scripts/build_logos_graph_regime_highlight_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "DF-P2-03" }
}

Write-Host "== pytest P2-03 ==" -ForegroundColor Cyan
py -m pytest tests/test_build_logos_graph_regime_highlight_v1.py -q
if ($LASTEXITCODE -ne 0) { $failed += "pytest" }

if (-not $SkipRegistry) {
    Write-Host "== unified registry + module registry ==" -ForegroundColor Cyan
    py scripts/mkm_unified_asset_registry_v1.py build
    if ($LASTEXITCODE -ne 0) { $failed += "registry" }
    py scripts/bootstrap_data_fabric_module_registry_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "module-registry" }
}

if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "P2+ next OK" -ForegroundColor Green
exit 0
