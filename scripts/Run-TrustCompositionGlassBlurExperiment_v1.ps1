# Trust Composition glass/blur experiment chain (B-track · research_only).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "`n=== glass/blur experiment gate ===" -ForegroundColor Cyan
& py scripts/check_trust_composition_glass_blur_experiment_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== clinic LOI gate (no regression) ===" -ForegroundColor Cyan
& py scripts/check_clinic_km_mmp_landing_gate_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nOK: Trust Composition glass/blur experiment chain completed." -ForegroundColor Green
exit 0
