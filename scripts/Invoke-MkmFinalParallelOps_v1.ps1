# Final parallel ops: fabric consume + DECOY D0/D1 + mkmlife §11 + branding matrix (NO LO-CG reopen)
param(
    [switch]$SkipFabric,
    [switch]$SkipDecoy,
    [switch]$SkipMkmlife,
    [switch]$SkipMsPasteWarn
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failed = @()

if (-not $SkipMsPasteWarn) {
    if (Test-Path "scripts/Invoke-MsRq019PastePackReadiness_v1.ps1") {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MsRq019PastePackReadiness_v1.ps1
        if ($LASTEXITCODE -ne 0) { Write-Host "warn: MS-PASTE" -ForegroundColor DarkYellow }
    }
}

if (-not $SkipFabric) {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-DataFabricParallelOps_v1.ps1 -SkipMsPasteReadiness
    if ($LASTEXITCODE -ne 0) { $failed += "fabric-ops" }
}

if (-not $SkipDecoy) {
    py scripts/bootstrap_decoy_experience_zone_shards_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "decoy-d0" }
    py scripts/check_decoy_d1_mkmlife_readiness_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "decoy-d1" }
}

if (-not $SkipMkmlife) {
    py scripts/check_mkmlife_section11_readiness_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "mkmlife-11" }
}

Write-Host "== pytest (decoy + registry + d1) ==" -ForegroundColor Cyan
py -m pytest tests/test_decoy_experience_layer_v1.py tests/test_mkm_unified_asset_registry_v1.py tests/test_check_decoy_d1_mkmlife_readiness_v1.py -q
if ($LASTEXITCODE -ne 0) { $failed += "pytest" }

if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "Final parallel ops OK" -ForegroundColor Green
exit 0
