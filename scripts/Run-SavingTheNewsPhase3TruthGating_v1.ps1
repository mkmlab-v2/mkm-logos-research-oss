# Phase 3 — Truth Gating stub + public-event ingest example.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsPhase3TruthGating_v1.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path 'docs/final/artifacts/saving_the_news_phase2_matrix_view_v1_latest.json')) {
    Write-Host "Phase2 matrix missing — running Phase2 chain first..." -ForegroundColor Yellow
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Run-SavingTheNewsPhase2Matrix_v1.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[1/3] eval truth gating..." -ForegroundColor Cyan
& py scripts/eval_saving_the_news_phase3_truth_gating_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Phase3 status..." -ForegroundColor Cyan
& py scripts/build_saving_the_news_phase3_poc_status_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] pytest..." -ForegroundColor Cyan
& py -m pytest tests/test_eval_saving_the_news_phase3_truth_gating_v1.py tests/test_build_saving_the_news_phase3_poc_status_v1.py -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Run-SavingTheNewsPhase3TruthGating_v1: OK" -ForegroundColor Green
exit 0
