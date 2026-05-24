#Requires -Version 5.1
<#
.SYNOPSIS
  Sequential closure bundle: (1) neutral margin experiment (2) weekly ops separation (3) feature RFC refresh.
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "==> [1/3] neutral abstain margin experiment" -ForegroundColor Cyan
py scripts\run_btrack_neutral_abstain_margin_experiment_v1.py
if ($LASTEXITCODE -ne 0) { throw "neutral margin exit $LASTEXITCODE" }

Write-Host "==> [2/3] weekly ops separation (VPS vs B-track)" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BtrackWeeklyOpsSeparation_v1.ps1
if ($LASTEXITCODE -ne 0) { throw "weekly ops separation exit $LASTEXITCODE" }

Write-Host "==> [3/3] feature RFC (JSON SSOT already in reports/)" -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath "reports\btrack_price_lens_feature_rfc_v1_latest.json")) {
    throw "Missing reports/btrack_price_lens_feature_rfc_v1_latest.json"
}
Write-Host "[OK] Sequential research closure complete" -ForegroundColor Green
