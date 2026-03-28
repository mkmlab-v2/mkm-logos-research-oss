<#
.SYNOPSIS
  Runs Dual Regime Fact-Lock pytest suite and writes REGIME_INTEGRITY_REPORT.json (session hook).

.DESCRIPTION
  From workspace root: py -m pytest projects/bitcoin-trading/tests/test_dual_regime_api_smoke.py
  Report: backtest_results/REGIME_INTEGRITY_REPORT.json

.EXAMPLE
  & c:\workspace\scripts\check-integrity.ps1
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "Workspace: $WorkspaceRoot"
Write-Host "Running Dual Regime integrity tests..."

& py -m pytest "projects/bitcoin-trading/tests/test_dual_regime_api_smoke.py" -v --tb=short
$exit = $LASTEXITCODE

$reportPath = Join-Path $WorkspaceRoot "backtest_results\REGIME_INTEGRITY_REPORT.json"
if (Test-Path -LiteralPath $reportPath) {
    Write-Host "REGIME_INTEGRITY_REPORT: $reportPath"
} else {
    Write-Host "Note: REGIME_INTEGRITY_REPORT.json not found (no regime tests collected or hook skipped)."
}

exit $exit
