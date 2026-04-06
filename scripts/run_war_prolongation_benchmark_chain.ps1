<#
.SYNOPSIS
  Run war-prolongation B-Track benchmark chain end-to-end.

.DESCRIPTION
  Observation-lane only chain for the war-prolongation hypothesis:
  1) Build multi-leg score from market data (XLE/ITA/VIX/WTI)
  2) Evaluate spot directional hit-rate
  3) Evaluate +N day windows (forward if available, trailing proxy fallback)
  4) Refresh AIDC perf/watt gate with isolated suffix
  5) Build single benchmark bundle JSON
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$OutputSuffix = "_war_20260406",
  [string]$Horizons = "1,5,20",
  [int]$GateIterations = 10,
  [string]$Period = "2y"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ($GateIterations -lt 1) { throw "GateIterations must be >= 1" }

$scorePath = Join-Path $WorkspaceRoot "docs/final/artifacts/btrack_prophecy_score_war_prolong_20260406_multileg.json"

Write-Host "==> build_war_prolongation_event_score.py"
& py (Join-Path $WorkspaceRoot "scripts/build_war_prolongation_event_score.py") --period $Period
if ($LASTEXITCODE -ne 0) { throw "build_war_prolongation_event_score.py failed: $LASTEXITCODE" }

Write-Host "==> eval_prophecy_hit_rate_v1.py (price)"
& py (Join-Path $WorkspaceRoot "scripts/eval_prophecy_hit_rate_v1.py") `
  --run-mode price `
  --score-json $scorePath `
  --output (Join-Path $WorkspaceRoot "docs/final/artifacts/prophecy_hit_rate_eval_war_prolong_20260406_multileg.json")
if ($LASTEXITCODE -ne 0) { throw "eval_prophecy_hit_rate_v1.py failed: $LASTEXITCODE" }

Write-Host "==> evaluate_war_prolongation_event_windows.py"
& py (Join-Path $WorkspaceRoot "scripts/evaluate_war_prolongation_event_windows.py") --horizons $Horizons
if ($LASTEXITCODE -ne 0) { throw "evaluate_war_prolongation_event_windows.py failed: $LASTEXITCODE" }

Write-Host "==> evaluate_war_prolongation_significance.py"
& py (Join-Path $WorkspaceRoot "scripts/evaluate_war_prolongation_significance.py")
if ($LASTEXITCODE -ne 0) { throw "evaluate_war_prolongation_significance.py failed: $LASTEXITCODE" }

Write-Host "==> update_aidc_kpi_gate.py baseline/treatment"
& py (Join-Path $WorkspaceRoot "scripts/update_aidc_kpi_gate.py") `
  --label baseline `
  --iterations $GateIterations `
  --measurement-mode inprocess `
  --output-suffix $OutputSuffix
if ($LASTEXITCODE -ne 0) { throw "update_aidc_kpi_gate.py baseline failed: $LASTEXITCODE" }

& py (Join-Path $WorkspaceRoot "scripts/update_aidc_kpi_gate.py") `
  --label treatment `
  --iterations $GateIterations `
  --measurement-mode inprocess `
  --output-suffix $OutputSuffix
if ($LASTEXITCODE -ne 0) { throw "update_aidc_kpi_gate.py treatment failed: $LASTEXITCODE" }

Write-Host "==> build_war_prolongation_benchmark_bundle.py"
& py (Join-Path $WorkspaceRoot "scripts/build_war_prolongation_benchmark_bundle.py")
if ($LASTEXITCODE -ne 0) { throw "build_war_prolongation_benchmark_bundle.py failed: $LASTEXITCODE" }

Write-Host "OK: war-prolongation benchmark chain completed." -ForegroundColor Green
Write-Host "Bundle: docs/final/artifacts/war_prolongation_benchmark_bundle_20260406.json"

