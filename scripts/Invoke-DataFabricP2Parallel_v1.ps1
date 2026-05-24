# P2 parallel: Lane B DF-P2-01 + MS paste readiness (지휘관 트랙 점검) + P1 smoke
param(
    [switch]$SkipMsPasteReadiness,
    [switch]$SkipP1Smoke
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failed = @()

if (-not $SkipMsPasteReadiness) {
    Write-Host "== MS-PASTE readiness (지휘관 트랙) ==" -ForegroundColor Yellow
    if (Test-Path "scripts/Invoke-MsRq019PastePackReadiness_v1.ps1") {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MsRq019PastePackReadiness_v1.ps1
        if ($LASTEXITCODE -ne 0) { $failed += "MS-PASTE-readiness" }
    } else {
        Write-Host "skip: Invoke-MsRq019PastePackReadiness_v1.ps1 missing" -ForegroundColor DarkYellow
    }
}

Write-Host "== DF-P2-01 pytest ==" -ForegroundColor Cyan
py -m pytest tests/test_resolve_logos_atom_anchor_verse_pool_v1.py -q
if ($LASTEXITCODE -ne 0) { $failed += "DF-P2-01-pytest" }

Write-Host "== DF-P2-01 sample resolve (codebook atom) ==" -ForegroundColor Cyan
py scripts/resolve_logos_atom_anchor_verse_pool_v1.py --atom-id "hebrew::אלהים" --max-rows 20000
if ($LASTEXITCODE -ne 0) {
    Write-Host "warn: sample resolve non-zero" -ForegroundColor DarkYellow
}

if (-not $SkipP1Smoke) {
    Write-Host "== P1 registry smoke ==" -ForegroundColor Cyan
    py scripts/mkm_unified_asset_registry_v1.py build
    if ($LASTEXITCODE -ne 0) { $failed += "P1-registry" }
}

if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "P2 parallel OK" -ForegroundColor Green
exit 0
