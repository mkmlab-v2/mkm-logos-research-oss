#Requires -Version 5.1
<#
.SYNOPSIS
  A2A dialogue bench repro bundle: pytest + fixed multi-scenario bench (--strict-exit).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-A2aDialogueBenchReproBundle_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-A2aDialogueBenchReproBundle_v1.ps1 -DryRun
#>
param(
    [int]$Turns = 4,
    [switch]$SkipPytest,
    [switch]$SkipRoutingCompare,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$benchScript = Join-Path $root 'scripts\build_a2a_dialogue_bench_v1.py'
$benchOut = Join-Path $root 'docs\final\artifacts\a2a_dialogue_bench_v1_latest.json'
$pytestTarget = 'tests/test_build_a2a_dialogue_bench_v1.py'

if (-not (Test-Path -LiteralPath $benchScript)) { throw "Missing: $benchScript" }

if (-not $SkipPytest) {
    Write-Host '== pytest ==' -ForegroundColor Cyan
    Write-Host "py -m pytest $pytestTarget -q --tb=short"
    if (-not $DryRun) {
        py -m pytest $pytestTarget -q --tb=short
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host '== a2a_dialogue_bench ==' -ForegroundColor Cyan
$benchLine = "py scripts/build_a2a_dialogue_bench_v1.py --turns $Turns --strict-exit --out $benchOut"
if ($SkipRoutingCompare) { $benchLine += ' --skip-routing-compare' }
Write-Host $benchLine
if (-not $DryRun) {
    if ($SkipRoutingCompare) {
        py scripts/build_a2a_dialogue_bench_v1.py --turns $Turns --strict-exit --out $benchOut --skip-routing-compare
    } else {
        py scripts/build_a2a_dialogue_bench_v1.py --turns $Turns --strict-exit --out $benchOut
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($DryRun) {
    Write-Host '[DRY-RUN] No commands executed.' -ForegroundColor Yellow
    exit 0
}

Write-Host "[DONE] A2A dialogue bench repro OK -> $benchOut" -ForegroundColor Green
exit 0
