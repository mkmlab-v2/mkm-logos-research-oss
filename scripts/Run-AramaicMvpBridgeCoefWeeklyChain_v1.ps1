#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly chain: regime-shift weight sweep → bridge coefficient recommendation artifact.

.DESCRIPTION
  B-track / research_only. SSOT: CONSTITUTION Aramaic MVP table (bridge coef row).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    throw "WorkspaceRoot not found: $WorkspaceRoot"
}

Push-Location $WorkspaceRoot
try {
    & py "scripts\run_aramaic_regime_shift_weight_sweep_v1.py"
    if ($LASTEXITCODE -ne 0) { throw "run_aramaic_regime_shift_weight_sweep_v1.py exited $LASTEXITCODE" }

    & py "scripts\apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py"
    if ($LASTEXITCODE -ne 0) { throw "apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py exited $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "[DONE] Aramaic MVP bridge-coef weekly chain (sweep -> apply)." -ForegroundColor Green
