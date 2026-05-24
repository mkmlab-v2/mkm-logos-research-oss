# Saving the News — Phase 1–3 internal PoC chain (research_only).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsFullRoadmap_v1.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Phase 1 readiness (NEWS-RT cohort) ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Run-SavingTheNewsParallelReadiness_v1.ps1') -FullCohortBench
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Phase 2 matrix ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Run-SavingTheNewsPhase2Matrix_v1.ps1')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Phase 3 truth gating ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Run-SavingTheNewsPhase3TruthGating_v1.ps1')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Showroom local smoke (optional slice + ingest) ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Run-SavingTheNewsShowroomLocalSmoke_v1.ps1')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Run-SavingTheNewsFullRoadmap_v1: OK (internal PoC only)" -ForegroundColor Green
exit 0
