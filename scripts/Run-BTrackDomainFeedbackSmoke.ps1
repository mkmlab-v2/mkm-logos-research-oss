# One-shot smoke for B-track "predict → measure → score" anchors (no A-track / live trade wiring).
# Pointers: docs/final/artifacts/mkm_ops_sync_bridge_v1.json
# Usage: pwsh -NoProfile -File scripts\Run-BTrackDomainFeedbackSmoke.ps1 [-SkipNews] [-SkipWeather] [-SkipGeneralProphecy]

param(
    [switch]$SkipNews,
    [switch]$SkipWeather,
    [switch]$SkipGeneralProphecy
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

if (-not $SkipGeneralProphecy) {
    Write-Host "`n=== [B] General prophecy registry/export pytest ===" -ForegroundColor Cyan
    & py -m pytest `
        tests/test_apply_general_prophecy_registry_patches_v1.py `
        tests/test_export_general_prophecy_to_jsonl.py `
        -q --tb=short
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipWeather) {
    Write-Host "`n=== [B] Weather GT triplet chain pytest ===" -ForegroundColor Cyan
    & py -m pytest tests/test_weather_gt_triplet_chain_smoke.py -q --tb=short
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipNews) {
    Write-Host "`n=== [B] News observation contract smoke ===" -ForegroundColor Cyan
    $newsPs1 = Join-Path $root "scripts\Run-NewsObservationContractSmoke.ps1"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $newsPs1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`nOK: B-track domain feedback smoke completed." -ForegroundColor Green
exit 0
