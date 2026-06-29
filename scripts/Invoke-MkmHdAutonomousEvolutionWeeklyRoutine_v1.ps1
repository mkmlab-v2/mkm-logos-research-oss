<#
.SYNOPSIS
  Weekly HD autonomous evolution routine — tier_0 full chain with hybrid batch.

.NOTES
  B-track [HYPO] only. No Track A / live / apply-active promotion.
#>
$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
Push-Location $workspaceRoot
try {
    $nlRepair = Join-Path $workspaceRoot "scripts\Invoke-NotebookLmMcpAuthAutoRepair_v1.ps1"
    if (Test-Path -LiteralPath $nlRepair) {
        Write-Host "=== NL MCP auth auto-repair (pre-HD-AE) ===" -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $nlRepair
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "NL auto-repair exit $LASTEXITCODE — continuing HD AE (vault/local SSOT still valid)"
        }
    }

    $runner = Join-Path $workspaceRoot "scripts\Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1"
    if (-not (Test-Path -LiteralPath $runner)) {
        throw "Missing runner: $runner"
    }

    $mission = if ($env:MKM_HD_AE_MISSION) {
        $env:MKM_HD_AE_MISSION
    } else {
        "P0+P1+완화P2 hybrid wiring + B-track intel + swarm observability (weekly auto)"
    }

    $lane = if ($env:MKM_HD_AE_LANE) { $env:MKM_HD_AE_LANE } else { "oracle" }

    & powershell -NoProfile -ExecutionPolicy Bypass -File $runner `
        -Mission $mission `
        -Lane $lane `
        -CostTier tier_0 `
        -IncludeP0P1P2Hybrid

    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    $digest = Join-Path $workspaceRoot "scripts\build_domain_prophecy_weekly_digest_v1.py"
    if (Test-Path -LiteralPath $digest) {
        Write-Host "=== domain prophecy weekly digest (P4) ===" -ForegroundColor Cyan
        & py $digest
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "domain prophecy digest exit $LASTEXITCODE — non-fatal for HD AE weekly"
        }
    }

    exit 0
}
finally {
    Pop-Location
}
