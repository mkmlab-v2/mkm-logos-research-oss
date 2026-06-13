#Requires -Version 5.1
<#
.SYNOPSIS
  A2A weekly repro bundle: dialogue bench + tp01-tp03 pilot + L1->L2 all-lanes chain + tp01 log + stack map.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-A2aWeeklyReproBundle_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-A2aWeeklyReproBundle_v1.ps1 -SkipDialogueBench
#>
param(
    [switch]$SkipDialogueBench,
    [switch]$SkipTargetPointsPilot,
    [switch]$SkipL1L2Chain,
    [switch]$SkipTp01Measurement,
    [switch]$SkipDogfoodAuto,
    [switch]$SkipStackMap,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Invoke-PyStep {
    param(
        [string]$Label,
        [string[]]$PyArgs
    )
    Write-Host "== $Label ==" -ForegroundColor Cyan
    Write-Host ("py " + ($PyArgs -join ' '))
    if ($DryRun) { return }
    py @PyArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipDialogueBench) {
    Write-Host '== dialogue bench repro ==' -ForegroundColor Cyan
    $dbArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'scripts\Run-A2aDialogueBenchReproBundle_v1.ps1')
    Write-Host ('powershell ' + ($dbArgs -join ' '))
    if (-not $DryRun) {
        powershell @dbArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

if (-not $SkipTargetPointsPilot) {
    Write-Host '== target points pilot (tp01-tp03) ==' -ForegroundColor Cyan
    $tpArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'scripts\Invoke-A2aTargetPointsPilotBundle_v1.ps1', '-StrictExit')
    Write-Host ('powershell ' + ($tpArgs -join ' '))
    if (-not $DryRun) {
        powershell @tpArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

if (-not $SkipL1L2Chain) {
    Write-Host '== L1->L2 chain (all lanes) ==' -ForegroundColor Cyan
    $l1Args = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'scripts\Run-A2aL1L2ChainPilot_v1.ps1', '-AllLanes', '-AppendLog', '-StrictExit')
    Write-Host ('powershell ' + ($l1Args -join ' '))
    if (-not $DryRun) {
        powershell @l1Args
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

if (-not $SkipTp01Measurement) {
    Invoke-PyStep -Label 'tp01 ops measurement log' -PyArgs @(
        'scripts/build_a2a_tp01_ops_measurement_v1.py', '--append-log', '--strict-exit'
    )
}

if (-not $SkipStackMap) {
    Invoke-PyStep -Label 'stack map + commander brief' -PyArgs @(
        'scripts/build_a2a_mkm_stack_four_layer_map_v1.py'
    )
}

if (-not $SkipDogfoodAuto) {
    Write-Host '== dogfood auto chain (L2 + Tier3 all lanes + report) ==' -ForegroundColor Cyan
    $dfArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'scripts\Run-A2aDogfoodAutoChain_v1.ps1')
    Write-Host ('powershell ' + ($dfArgs -join ' '))
    if (-not $DryRun) {
        powershell @dfArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Invoke-PyStep -Label 'IR draft rebuild' -PyArgs @(
    'scripts/build_a2a_inter_agent_encoding_ir_draft_v1.py'
)

Invoke-PyStep -Label 'cursor dogfood peer brief check' -PyArgs @(
    'scripts/check_a2a_cursor_dogfood_peer_brief_v1.py', '--strict-exit'
)

if ($DryRun) {
    Write-Host '[DRY-RUN] No commands executed.' -ForegroundColor Yellow
    exit 0
}

Write-Host '[DONE] A2A weekly repro bundle OK' -ForegroundColor Green
exit 0
