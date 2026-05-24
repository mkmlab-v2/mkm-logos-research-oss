# Parallel ops: fabric P2 consume + DECOY-P0 + mkmlife §11 pointer (NO LO-CG reopen)
param(
    [switch]$SkipFabricConsume,
    [switch]$SkipDecoy,
    [switch]$SkipMkmlife,
    [switch]$SkipMsPasteWarn
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failed = @()

if (-not $SkipMsPasteWarn) {
    Write-Host "== MS-PASTE (warn-only) ==" -ForegroundColor Yellow
    if (Test-Path "scripts/Invoke-MsRq019PastePackReadiness_v1.ps1") {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MsRq019PastePackReadiness_v1.ps1
        if ($LASTEXITCODE -ne 0) { Write-Host "warn: MS-PASTE exit $LASTEXITCODE" -ForegroundColor DarkYellow }
    }
}

if (-not $SkipFabricConsume) {
    Write-Host "== Fabric P2 consume (registry + graph bundle; NO LO-CG) ==" -ForegroundColor Cyan
    py scripts/mkm_unified_asset_registry_v1.py build
    if ($LASTEXITCODE -ne 0) { $failed += "registry" }
    py scripts/build_logos_corpus_graph_bundle_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "graph-bundle" }
    py scripts/bootstrap_data_fabric_module_registry_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "module-registry" }
}

if (-not $SkipDecoy) {
    Write-Host "== DECOY-P0 D0 ==" -ForegroundColor Cyan
    py scripts/bootstrap_decoy_experience_zone_shards_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "DECOY-P0" }
}

if (-not $SkipMkmlife) {
    Write-Host "== MKMLIFE §11 MVP pointer ==" -ForegroundColor Cyan
    py scripts/check_mkmlife_section11_readiness_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "MKMLIFE-11" }
}

Write-Host "== pytest decoy + registry ==" -ForegroundColor Cyan
py -m pytest tests/test_decoy_experience_layer_v1.py tests/test_mkm_unified_asset_registry_v1.py -q
if ($LASTEXITCODE -ne 0) { $failed += "pytest" }

if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "Parallel ops OK (fabric consume + DECOY + mkmlife §11)" -ForegroundColor Green
exit 0
