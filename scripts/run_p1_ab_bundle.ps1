<#
.SYNOPSIS
  Run P1 A/B profiles and generate final selection.

.DESCRIPTION
  Executes:
  1) efficiency_first
  2) intensity_first
  3) balanced
  4) final selection report

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_p1_ab_bundle.ps1
#>
param()

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $workspaceRoot

Write-Host '== P1 A/B: efficiency_first ==' -ForegroundColor Cyan
& py (Join-Path $workspaceRoot 'scripts\run_p1_efficiency_ab.py') --profile efficiency_first
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== P1 A/B: intensity_first ==' -ForegroundColor Cyan
& py (Join-Path $workspaceRoot 'scripts\run_p1_efficiency_ab.py') --profile intensity_first
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== P1 A/B: balanced ==' -ForegroundColor Cyan
& py (Join-Path $workspaceRoot 'scripts\run_p1_efficiency_ab.py') --profile balanced
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== P1 A/B: final selection ==' -ForegroundColor Cyan
& py (Join-Path $workspaceRoot 'scripts\report_p1_final_selection.py')
exit $LASTEXITCODE
