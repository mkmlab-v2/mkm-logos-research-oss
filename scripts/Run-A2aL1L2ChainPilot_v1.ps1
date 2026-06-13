#Requires -Version 5.1
<#
.SYNOPSIS
  L1 lane inject → L2 Trust Packet chain pilot (default: infra + ms lanes).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-A2aL1L2ChainPilot_v1.ps1
#>
param(
    [switch]$AllLanes,
    [switch]$AppendLog,
    [switch]$StrictExit
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$argsList = @('scripts/build_a2a_l1_l2_chain_pilot_v1.py', '--strict-exit')
if ($AllLanes) { $argsList += '--all-lanes' }
if ($AppendLog) { $argsList += '--append-log' }
if (-not $StrictExit) {
    $argsList = $argsList | Where-Object { $_ -ne '--strict-exit' }
}

Write-Host '== L1->L2 chain pilot ==' -ForegroundColor Cyan
py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host '[DONE] L1->L2 chain pilot OK' -ForegroundColor Green
