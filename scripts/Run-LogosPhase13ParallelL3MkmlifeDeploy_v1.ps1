# Phase13: Commander L3 ACK + parallel L3 swap/VPS + mkmlife deploy + showroom + closure
param(
    [switch]$SkipVpsL3Sync,
    [switch]$SkipShowroomSync,
    [switch]$SkipMkmlifeDeploy,
    [switch]$FullMkmlifeDeploy,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$L3Notes = "Commander explicit L3 approval — Phase13 parallel push"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> Phase13 serial: L3 commander record" -ForegroundColor Cyan
& $py scripts/record_logos_rag_btrack_promotion_human_approval_v1.py --tier L3 --force --notes $L3Notes
if ($LASTEXITCODE -ne 0) { throw "L3 record" }

$trackL3 = {
    Set-Location $using:WorkspaceRoot
    $py = $using:py
    & $py scripts/apply_logos_rag_l3_production_st_index_v1.py
    if ($LASTEXITCODE -ne 0) { throw "l3 swap" }
    if (-not $using:SkipVpsL3Sync) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Sync-LogosRagL3ProdIndexToVps_v1.ps1
        if ($LASTEXITCODE -ne 0) { throw "l3 vps sync" }
    }
}

$trackMkmlife = {
    if ($using:SkipMkmlifeDeploy) { return }
    Set-Location $using:WorkspaceRoot
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/Invoke-Op30Phase2Daily_v1.ps1")
    if ($using:FullMkmlifeDeploy) { $args += "-FullDeploy" } else { $args += "-DeployAssets" }
    & powershell @args
    if ($LASTEXITCODE -ne 0) { throw "mkmlife deploy" }
}

$trackShowroom = {
    Set-Location $using:WorkspaceRoot
    $py = $using:py
    if (-not $using:SkipShowroomSync) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_showroom_to_vps.ps1
        if ($LASTEXITCODE -ne 0) { throw "showroom vps" }
    }
    & $py scripts/check_showroom_trust_viz_public_chain_v1.py
    if ($LASTEXITCODE -ne 0) { throw "showroom smoke" }
    & $py scripts/build_logos_phase12_live_bundle_v1.py
    if ($LASTEXITCODE -ne 0) { throw "live bundle" }
}

$trackRag = {
    Set-Location $using:WorkspaceRoot
    $py = $using:py
    & $py scripts/apply_logos_rag_q01_theology_primary_order_v1.py
    if ($LASTEXITCODE -ne 0) { throw "q01" }
    & $py scripts/run_logos_rag_dual_gold_eval_v1.py
    if ($LASTEXITCODE -ne 0) { throw "dual eval" }
    & $py scripts/build_logos_rag_l3_readiness_v1.py
    if ($LASTEXITCODE -ne 0) { throw "l3 readiness" }
    & $py scripts/check_logos_rag_btrack_promotion_gate_v1.py --run-pytest
    if ($LASTEXITCODE -ne 0) { throw "gate pytest" }
    & $py scripts/build_logos_rag_promotion_review_packet_v1.py
    if ($LASTEXITCODE -ne 0) { throw "review packet" }
}

$jobs = @(
    (Start-Job -Name L3SwapVps -ScriptBlock $trackL3)
    (Start-Job -Name MkmlifeDeploy -ScriptBlock $trackMkmlife)
    (Start-Job -Name ShowroomLive -ScriptBlock $trackShowroom)
    (Start-Job -Name RagGate -ScriptBlock $trackRag)
)

Write-Host "==> Phase13 parallel: $($jobs.Count) tracks" -ForegroundColor Cyan
$jobs | Wait-Job | Out-Null
foreach ($j in $jobs) {
    if ($j.State -eq "Failed") {
        Receive-Job -Job $j -ErrorAction SilentlyContinue | Write-Host
        throw "Track $($j.Name) failed"
    }
    Write-Host "--- $($j.Name) ---" -ForegroundColor DarkCyan
    Receive-Job -Job $j | Write-Host
    Remove-Job -Job $j
}

Write-Host "==> Phase13 merge: signoff + CDIM + envelope + probe + closure" -ForegroundColor Cyan
& $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --commander-direct-signoff
if ($LASTEXITCODE -ne 0) { throw "signoff" }
& $py scripts/build_logos_concept_bridge_registry_v1.py
& $py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
if ($LASTEXITCODE -ne 0) { throw "cdim" }
& $py scripts/assemble_three_lens_sphere_envelope_v1.py --validate-schema --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { throw "envelope" }
& $py scripts/probe_mkmlife_magic_orb_live_v1.py
if ($LASTEXITCODE -ne 0) { throw "mkmlife probe" }
& $py scripts/build_logos_100pct_closure_v1.py --run-pytest --strict
if ($LASTEXITCODE -ne 0) { throw "closure" }

Write-Host "==> Phase13 L3 + mkmlife parallel push done" -ForegroundColor Green
