# Trust Composition — clinic LOI full readiness (landing + Figma reverse-sync + tracker refresh).
param(
    [switch]$FetchFigma,
    [switch]$SkipFigma,
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "`n=== [1/3] clinic LOI landing design chain ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-ClinicLoiLandingDesignChain_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipFigma) {
    Write-Host "`n=== [2/3] clinic LOI Figma reverse-sync ===" -ForegroundColor Cyan
    $figmaArgs = @('-File', 'scripts/Run-ClinicLoiFigmaReverseSyncAuto_v1.ps1')
    if ($FetchFigma) { $figmaArgs += '-FetchFigma' }
    if ($SkipPytest) { $figmaArgs += '-SkipPytest' }
    & powershell -NoProfile -ExecutionPolicy Bypass @figmaArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "`n=== [2/3] Figma reverse-sync SKIPPED ===" -ForegroundColor Yellow
}

Write-Host "`n=== [3/3] tracker readiness refresh ===" -ForegroundColor Cyan
& py scripts/build_clinic_km_mmp_loi_tracker_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py scripts/check_clinic_km_mmp_loi_tracker_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipPytest) {
    & py -m pytest tests/test_clinic_km_mmp_loi_tracker_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`nOK: Trust Composition clinic LOI full readiness completed." -ForegroundColor Green
exit 0
