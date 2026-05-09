<#
.SYNOPSIS
  Weekly / pre-presentation evidence cadence (융합 권장 순서의 "운영 증거" 부분).

.DESCRIPTION
  1) P0 constitution path gate (verify_p0_constitution_gate_paths.ps1)
  2) Trading Guardian bundle (Run-TradingGuardianBundleTask.ps1) — optional
  3) GO stability cycle once, orchestrator skipped by default (run_mkm_orchestrator_go_stability_cycle_v1.ps1) — optional
  4) Conditional GO+ report v2 (build_mkm_conditional_go_plus_report_v2.py)

  Heavy optional: -IncludeAcceleratedBurnIn calls run_mkm_orchestrator_accelerated_burnin_v1.ps1
  (long-running; use before major demos only).

.EXAMPLE
  pwsh -File scripts\Run-MkmWeeklyOperationalEvidenceCadence.ps1

.EXAMPLE
  pwsh -File scripts\Run-MkmWeeklyOperationalEvidenceCadence.ps1 -IncludeGoStabilityCycle -SkipTradingGuardian
#>
[CmdletBinding()]
param(
  [string]$WorkspaceRoot = "",
  [switch]$SkipP0,
  [switch]$SkipTradingGuardian,
  [switch]$SkipGoPlusReport,
  [int]$GoPlusWindowHours = 24,
  [switch]$IncludeGoStabilityCycle,
  [switch]$IncludeAcceleratedBurnIn,
  [ValidateRange(1, 500)]
  [int]$BurnInIterations = 12,
  [ValidateRange(0, 600)]
  [int]$BurnInSleepSeconds = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  }
  else {
    $WorkspaceRoot = (Get-Location).Path
  }
}

Set-Location -LiteralPath $WorkspaceRoot

$p0 = Join-Path $WorkspaceRoot "scripts\verify_p0_constitution_gate_paths.ps1"
$tg = Join-Path $WorkspaceRoot "scripts\Run-TradingGuardianBundleTask.ps1"
$cycle = Join-Path $WorkspaceRoot "scripts\run_mkm_orchestrator_go_stability_cycle_v1.ps1"
$burn = Join-Path $WorkspaceRoot "scripts\run_mkm_orchestrator_accelerated_burnin_v1.ps1"
$goPlus = Join-Path $WorkspaceRoot "scripts\build_mkm_conditional_go_plus_report_v2.py"

if (-not $SkipP0) {
  if (-not (Test-Path -LiteralPath $p0)) { throw "Missing: $p0" }
  powershell -NoProfile -ExecutionPolicy Bypass -File $p0
  if ($LASTEXITCODE -ne 0) { throw "P0 constitution gate failed (exit=$LASTEXITCODE)" }
  Write-Host "[ok] P0 constitution gate"
}

if (-not $SkipTradingGuardian) {
  if (-not (Test-Path -LiteralPath $tg)) { throw "Missing: $tg" }
  pwsh -NoProfile -ExecutionPolicy Bypass -File $tg -WorkspaceRoot $WorkspaceRoot
  if ($LASTEXITCODE -ne 0) { throw "Trading Guardian bundle failed (exit=$LASTEXITCODE)" }
  Write-Host "[ok] Trading Guardian bundle"
}

if ($IncludeAcceleratedBurnIn) {
  if (-not (Test-Path -LiteralPath $burn)) { throw "Missing: $burn" }
  & pwsh -NoProfile -ExecutionPolicy Bypass -File $burn `
    -WorkspaceRoot $WorkspaceRoot `
    -Iterations $BurnInIterations `
    -SleepSeconds $BurnInSleepSeconds `
    -RebuildGoPlusReport `
    -ReportTailMatchIterations
  if ($LASTEXITCODE -ne 0) { throw "Accelerated burn-in failed (exit=$LASTEXITCODE)" }
  Write-Host "[ok] Accelerated burn-in + GO+ rebuild"
}
elseif ($IncludeGoStabilityCycle) {
  if (-not (Test-Path -LiteralPath $cycle)) { throw "Missing: $cycle" }
  pwsh -NoProfile -ExecutionPolicy Bypass -File $cycle -WorkspaceRoot $WorkspaceRoot -SkipOrchestratorRun
  if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) {
    throw "GO stability cycle unexpected exit=$LASTEXITCODE"
  }
  Write-Host "[ok] GO stability cycle (orchestrator skipped; exit=$LASTEXITCODE acceptable WATCH/HOLD)"
}

if (-not $SkipGoPlusReport -and -not $IncludeAcceleratedBurnIn) {
  if (-not (Test-Path -LiteralPath $goPlus)) { throw "Missing: $goPlus" }
  py $goPlus --window-hours $GoPlusWindowHours
  if ($LASTEXITCODE -ne 0) { throw "Conditional GO+ report failed (exit=$LASTEXITCODE)" }
  Write-Host "[ok] Conditional GO+ report v2"
}

Write-Host "[done] MkmWeeklyOperationalEvidenceCadence"
exit 0
