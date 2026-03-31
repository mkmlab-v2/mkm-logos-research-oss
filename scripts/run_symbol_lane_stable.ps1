<#
.SYNOPSIS
  Run B-Track symbol lane gate+lock in stable mode.

.DESCRIPTION
  Uses production-stable gate template and extraction defaults.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_symbol_lane_stable.ps1
#>
param()

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$runner = Join-Path $workspaceRoot 'scripts\run_btrack_symbol_lane_gate_and_lock.py'
$gateTemplate = Join-Path $workspaceRoot 'data\logos\btrack_pilot\gates\symbol_lane_gate_template.json'
$baselineOut = Join-Path $workspaceRoot 'reports\constitution\btrack_pilot\btrack_symbol_lane_baseline_lock_stable_latest.json'

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if (-not (Test-Path -LiteralPath $gateTemplate)) {
    throw "Gate template not found: $gateTemplate"
}

Set-Location -LiteralPath $workspaceRoot
Write-Host '== Symbol Lane Stable ==' -ForegroundColor Cyan
& py $runner --extract-min-df 2 --profile-tag stable --gate-template $gateTemplate --baseline-out $baselineOut
exit $LASTEXITCODE
