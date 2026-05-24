# Phase 2 — Multi-Lens Matrix View chain (Saving the News).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsPhase2Matrix_v1.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[1/4] refresh news/macro adapters..." -ForegroundColor Cyan
& py scripts/build_btrack_news_macro_lens_adapters_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/4] build Phase2 matrix view..." -ForegroundColor Cyan
& py scripts/build_saving_the_news_phase2_matrix_view_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/4] Phase2 PoC status..." -ForegroundColor Cyan
& py scripts/build_saving_the_news_phase2_poc_status_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/4] pytest..." -ForegroundColor Cyan
& py -m pytest tests/test_build_saving_the_news_phase2_matrix_view_v1.py tests/test_build_saving_the_news_phase2_poc_status_v1.py -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Run-SavingTheNewsPhase2Matrix_v1: OK" -ForegroundColor Green
exit 0
