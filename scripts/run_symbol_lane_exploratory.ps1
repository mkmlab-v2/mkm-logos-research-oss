<#
.SYNOPSIS
  Run B-Track symbol lane gate+lock in exploratory mode.

.DESCRIPTION
  Uses exploratory gate template with low-DF extraction for DSS expansion tests.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_symbol_lane_exploratory.ps1
#>
param()

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$runner = Join-Path $workspaceRoot 'scripts\run_btrack_symbol_lane_gate_and_lock.py'
$gateTemplate = Join-Path $workspaceRoot 'data\logos\btrack_pilot\gates\symbol_lane_gate_template_exploratory.json'
$baselineOut = Join-Path $workspaceRoot 'reports\constitution\btrack_pilot\btrack_symbol_lane_baseline_lock_exploratory_latest.json'

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if (-not (Test-Path -LiteralPath $gateTemplate)) {
    throw "Gate template not found: $gateTemplate"
}

Set-Location -LiteralPath $workspaceRoot
Write-Host '== Symbol Lane Exploratory ==' -ForegroundColor Cyan
& py $runner --extract-min-df 1 --profile-tag exploratory --gate-template $gateTemplate --baseline-out $baselineOut
exit $LASTEXITCODE
