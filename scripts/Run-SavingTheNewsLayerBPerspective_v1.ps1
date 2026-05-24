# Layer B — perspective appendix + flywheel A/S snapshot (Saving the News, research_only).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsLayerBPerspective_v1.ps1

param(
    [switch]$SkipPatchMatrix
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[1/3] flywheel A/S transparency snapshot..." -ForegroundColor Cyan
& py scripts/build_saving_the_news_flywheel_as_snapshot_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Layer B perspective appendix (GraphRAG + lens snapshots)..." -ForegroundColor Cyan
$patchArgs = @()
if (-not $SkipPatchMatrix) { $patchArgs += '--patch-matrix' }
& py scripts/build_saving_the_news_perspective_appendix_v1.py @patchArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] pytest Layer B..." -ForegroundColor Cyan
& py -m pytest tests/test_build_saving_the_news_perspective_appendix_v1.py tests/test_build_saving_the_news_flywheel_as_snapshot_v1.py -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Run-SavingTheNewsLayerBPerspective_v1: OK" -ForegroundColor Green
exit 0
