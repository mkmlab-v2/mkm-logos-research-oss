# Clinic LOI Figma reverse-sync — auto pack + sync + reference screenshot + gate.
param(
    [switch]$FetchFigma,
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$gateArgs = @('scripts/check_clinic_loi_figma_reverse_sync_gate_v1.py')
if ($FetchFigma) { $gateArgs += '--fetch-figma' }

& py @gateArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipPytest) {
    & py -m pytest tests/test_clinic_loi_figma_reverse_sync_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK: clinic LOI Figma reverse-sync auto completed." -ForegroundColor Green
exit 0
