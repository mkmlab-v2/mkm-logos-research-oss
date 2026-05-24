# Phase11: bridge signoff refresh + registry/closure + optional VPS sync + weekly task register
param(
    [switch]$SkipVpsSync,
    [switch]$SkipWeeklyRegister,
    [switch]$SkipClosurePytest,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> Phase11: bridge commander signoff refresh" -ForegroundColor Cyan
& $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --commander-direct-signoff
if ($LASTEXITCODE -ne 0) { throw "bridge signoff" }

& $py scripts/build_logos_concept_bridge_registry_v1.py
if ($LASTEXITCODE -ne 0) { throw "bridge registry" }

& $py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
if ($LASTEXITCODE -ne 0) { throw "cdim" }

Write-Host "==> closure + smoke" -ForegroundColor Cyan
if ($SkipClosurePytest) {
    & $py scripts/build_logos_100pct_closure_v1.py
} else {
    & $py scripts/build_logos_100pct_closure_v1.py --run-pytest
}
if ($LASTEXITCODE -ne 0) { throw "closure" }

& $py scripts/check_showroom_trust_viz_public_chain_v1.py
if ($LASTEXITCODE -ne 0) { throw "smoke" }

if (-not $SkipVpsSync) {
    Write-Host "==> VPS sync (no RefreshStaging)" -ForegroundColor Cyan
    $env:JEMAAI_VPS_RELOAD_NGINX = "1"
    if (Get-Command pwsh -ErrorAction SilentlyContinue) {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\sync_showroom_to_vps.ps1
    } else {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\sync_showroom_to_vps.ps1
    }
    if ($LASTEXITCODE -ne 0) { throw "vps sync" }
}

if (-not $SkipWeeklyRegister) {
    Write-Host "==> register weekly Phase10 4RAG task" -ForegroundColor Cyan
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\Register-LogosPhase10FourRagWeeklyTask.ps1
    if ($LASTEXITCODE -ne 0) { throw "weekly register" }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-LogosPhase10FourRagWeeklyTask_v1.ps1
    if ($LASTEXITCODE -ne 0) { throw "weekly verify" }
}

Write-Host "==> Phase11 governance + ops done" -ForegroundColor Green
