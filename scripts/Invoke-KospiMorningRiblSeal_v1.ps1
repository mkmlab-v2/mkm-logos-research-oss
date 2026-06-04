#Requires -Version 5.1
<#
.SYNOPSIS
  KOSPI morning R-IBL seal: Phase B overnight overlay + brief + executive + prediction registry.

.DESCRIPTION
  research_only · B-track [HYPO]. Run after overnight CSV/signals exist (daily chain 08:00 or manual fetch).
  Evening score uses reports/briefing_log/*_research_seal_v1.json from this step.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipPhaseB,
    [switch]$SkipExecutive
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }

if (-not $SkipPhaseB) {
    Write-Host "==> run_kospi_hypothesis_reroute_phase_b_v1.py" -ForegroundColor Cyan
    & $py scripts/run_kospi_hypothesis_reroute_phase_b_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "==> build_internal_kospi_morning_brief_onepager_v1.py" -ForegroundColor Cyan
& $py scripts/build_internal_kospi_morning_brief_onepager_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipExecutive) {
    Write-Host "==> build_kospi_integrated_executive_onepager_v1.py" -ForegroundColor Cyan
    & $py scripts/build_kospi_integrated_executive_onepager_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "==> build_research_morning_prediction_registry_v1.py" -ForegroundColor Cyan
& $py scripts/build_research_morning_prediction_registry_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] KOSPI morning R-IBL seal complete." -ForegroundColor Green
exit 0
