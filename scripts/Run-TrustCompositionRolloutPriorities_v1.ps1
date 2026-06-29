# Trust Composition rollout — priorities + top-surface gates.
param(
    [switch]$SkipDesignLane,
    [switch]$IncludeMagicOrbChain
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "`n=== [1/4] rollout priorities ===" -ForegroundColor Cyan
& py scripts/build_trust_composition_rollout_priorities_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== [2/4] clinic LOI landing gate ===" -ForegroundColor Cyan
& py scripts/check_clinic_km_mmp_landing_gate_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($IncludeMagicOrbChain) {
    Write-Host "`n=== [3/4] magic orb design readiness chain ===" -ForegroundColor Cyan
    & py scripts/run_magic_orb_design_readiness_chain_v1.py --skip-pytest
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py scripts/build_trust_composition_rollout_priorities_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipDesignLane) {
    $step = if ($IncludeMagicOrbChain) { "[4/4]" } else { "[3/3]" }
    Write-Host "`n=== $step design lane routine ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmDesignLaneRoutine_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`nOK: Trust Composition rollout chain completed." -ForegroundColor Green
exit 0
