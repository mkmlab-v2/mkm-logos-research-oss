# Trust Composition chain — clinic LOI landing (dry gate + tracker).
# Analogue: Run-AudioBgmEconomyChain_v1.ps1 (Phase A always · Phase B optional)

param(
    [switch]$SkipTracker
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "`n=== [1/2] clinic LOI landing design gate (DTCG v2 · copy · contrast) ===" -ForegroundColor Cyan
& py scripts/check_clinic_km_mmp_landing_gate_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipTracker) {
    Write-Host "`n=== [2/2] LOI tracker structure ===" -ForegroundColor Cyan
    & py scripts/check_clinic_km_mmp_loi_tracker_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`nOK: Clinic LOI landing design chain completed." -ForegroundColor Green
exit 0
