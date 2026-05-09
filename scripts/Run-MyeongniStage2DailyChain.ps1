<#
.SYNOPSIS
  Daily Stage2 maintenance chain for myeongni.
  1) Realset gate check
  2) Optional realset backfill build when gate fails
  3) Stage2 apply chain with strict gate
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$MinRealCount = 50,
    [int]$BuildTargetCount = 60,
    [switch]$AutoBackfillRealset
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$gateJson = Join-Path $WorkspaceRoot "docs\final\artifacts\myeongni_stage2_realset_gate_latest.json"

& py "scripts\run_myeongni_stage2_realset_gate_v1.py" --min-real-count "$MinRealCount" --output-json "$gateJson"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$gate = Get-Content -LiteralPath $gateJson -Raw | ConvertFrom-Json
$pass = [bool]$gate.pass

if (-not $pass -and $AutoBackfillRealset) {
    & py "scripts\run_myeongni_stage2_build_realset_v1.py" --target-count "$BuildTargetCount"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& py "scripts\apply_myeongni_stage2_calibration_v1.py" --realset-min-count "$MinRealCount" --strict-realset-gate
exit $LASTEXITCODE
