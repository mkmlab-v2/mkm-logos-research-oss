# Clinic LOI Figma emergency bootstrap — env normalize + discover + full chain.
param(
    [string]$ProvisionalFileKey = "8Ey3MEkXhH8EliARQ9OydE",
    [switch]$SkipFullChain
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "`n=== [1/4] normalize .env Figma keys ===" -ForegroundColor Cyan
& py scripts/bootstrap_clinic_loi_figma_env_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== [2/4] discover mkm-20260624 file ===" -ForegroundColor Cyan
& py scripts/discover_clinic_loi_figma_file_v1.py --write-ssot
$discEc = $LASTEXITCODE
if ($discEc -ne 0) {
    Write-Host "WARN: mkm-20260624 not in team projects — using provisional file key $ProvisionalFileKey" -ForegroundColor Yellow
    & py scripts/bootstrap_clinic_loi_figma_env_v1.py --file-key $ProvisionalFileKey
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py scripts/discover_clinic_loi_figma_file_v1.py --write-ssot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipFullChain) {
    Write-Host "`n=== [3/4] clinic LOI Figma live sync ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-ClinicLoiFigmaReverseSyncAuto_v1.ps1 -FetchFigma
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "`n=== [4/4] clinic LOI full readiness ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-TrustCompositionClinicLoiFull_v1.ps1 -FetchFigma -SkipFigma
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`nOK: clinic LOI Figma bootstrap completed." -ForegroundColor Green
exit 0
