#Requires -Version 5.1
<#
.SYNOPSIS
  Multi-Res Index delegation routine v1 — pytest, index build, ops overlay, AUTO chain.

.DESCRIPTION
  SSOT: reports/multi_res_index_delegation_v1_latest.json
  승인표: reports/delegation_multi_res_index_approval_map_v1_latest.json
  research_only · Track A / live / apply-active 금지.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MultiResIndexDelegationRoutine_v1.ps1
  powershell … -DryRun
#>
param(
    [switch]$DryRun,
    [switch]$SkipP0,
    [switch]$SkipOpsOverlay
)

$ErrorActionPreference = 'Stop'
$Root = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

Push-Location -LiteralPath $Root
try {
    if (-not $SkipP0) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'verify_p0_constitution_gate_paths.ps1')
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    & py -m pytest tests/test_multi_res_index_v1.py tests/test_multi_res_fills_join_v1.py tests/test_multi_res_drift_recovery_drill_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if ($DryRun) {
        Write-Host 'DRY-RUN OK: pytest passed; skipping index build and delegation'
        exit 0
    }

    & py scripts/multi_res_fills_join_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not $SkipOpsOverlay) {
        & py scripts/build_mkm_ops_memory_fills_overlay_v1.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    & py scripts/run_multi_res_index_delegation_v1.py
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
