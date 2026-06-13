#Requires -Version 5.1
<#
.SYNOPSIS
  Auto dogfood chain: L2 shadow + Tier3 all lanes + longitudinal report.

.EXAMPLE
  powershell -File scripts\Run-A2aDogfoodAutoChain_v1.ps1
#>
param(
    [switch]$SkipL2Shadow,
    [switch]$SkipTier3AllLanes,
    [switch]$SkipLongitudinalReport,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Invoke-PyStep {
    param([string]$Label, [string[]]$PyArgs)
    Write-Host "== $Label ==" -ForegroundColor Cyan
    Write-Host ("py " + ($PyArgs -join ' '))
    if ($DryRun) { return }
    py @PyArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipL2Shadow) {
    Invoke-PyStep -Label 'L2 shadow (commander default)' -PyArgs @(
        'scripts/build_a2a_l2_shadow_measurement_v1.py', '--append-log', '--strict-exit'
    )
}

if (-not $SkipTier3AllLanes) {
    foreach ($lane in @('oracle', 'ms', 'infra', 'web_ops')) {
        Invoke-PyStep -Label "Tier3 wire handoff ($lane)" -PyArgs @(
            'scripts/build_a2a_tier3_cursor_wire_handoff_pilot_v1.py',
            '--lane', $lane, '--append-log', '--strict-exit'
        )
    }
}

if (-not $SkipLongitudinalReport) {
    Invoke-PyStep -Label 'dogfood longitudinal report' -PyArgs @(
        'scripts/build_a2a_dogfood_longitudinal_report_v1.py', '--strict-exit'
    )
}

if ($DryRun) {
    Write-Host '[DRY-RUN] No commands executed.' -ForegroundColor Yellow
    exit 0
}

Write-Host '[DONE] A2A dogfood auto chain OK' -ForegroundColor Green
exit 0
