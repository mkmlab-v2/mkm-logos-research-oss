# Phase14: full sweep — 4RAG + Track C publish + VPS RAG live + mkmlife + closure
param(
    [switch]$SkipShowroomPublish,
    [switch]$SkipVpsSync,
    [switch]$SkipMkmlifeDeploy,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$trackFourRag = {
    Set-Location $using:WorkspaceRoot
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-LogosPhase10FourRagEnvelopeRefresh_v1.ps1 -SkipOlAtoms -SkipVpsSync
    if ($LASTEXITCODE -ne 0) { throw "phase10 4rag" }
}

$trackShowroom = {
    if ($using:SkipShowroomPublish) { return }
    Set-Location $using:WorkspaceRoot
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ShowroomTrackCPublishRoutine_v1.ps1 -SkipVpsSync
    if ($LASTEXITCODE -ne 0) { throw "showroom publish" }
}

$trackVpsRag = {
    Set-Location $using:WorkspaceRoot
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LogosRagVpsLiveParallel_v1.ps1
    if ($LASTEXITCODE -ne 0) { throw "vps rag live" }
}

$trackMkmlife = {
    if ($using:SkipMkmlifeDeploy) { return }
    Set-Location $using:WorkspaceRoot
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-Op30Phase2Daily_v1.ps1 -DeployAssets
    if ($LASTEXITCODE -ne 0) { throw "mkmlife deploy" }
}

$trackCommercial = {
    Set-Location $using:WorkspaceRoot
    $py = $using:py
    & $py scripts/build_logos_observatory_commercial_readiness_v1.py
    if ($LASTEXITCODE -ne 0) { throw "commercial" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-LogosCrossDomainInterfaceParallel_v1.ps1 -SkipLens -Validate
    if ($LASTEXITCODE -ne 0) { throw "cdim" }
    & $py scripts/build_showroom_cdim_slice_v1.py
    if ($LASTEXITCODE -ne 0) { throw "cdim slice" }
    & $py scripts/build_mkm_trackc_ops_dashboard_v1.py
    if ($LASTEXITCODE -ne 0) { throw "dashboard" }
}

$jobs = @(
    (Start-Job -Name FourRag -ScriptBlock $trackFourRag)
    (Start-Job -Name ShowroomPublish -ScriptBlock $trackShowroom)
    (Start-Job -Name VpsRagLive -ScriptBlock $trackVpsRag)
    (Start-Job -Name MkmlifeDeploy -ScriptBlock $trackMkmlife)
    (Start-Job -Name CommercialCdim -ScriptBlock $trackCommercial)
)

Write-Host "==> Phase14 parallel: $($jobs.Count) tracks" -ForegroundColor Cyan
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

Write-Host "==> Phase14 merge: signoff + unified VPS + probes + sweep + closure" -ForegroundColor Cyan
& $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --commander-direct-signoff
if ($LASTEXITCODE -ne 0) { throw "signoff" }
& $py scripts/build_logos_concept_bridge_registry_v1.py
& $py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
if ($LASTEXITCODE -ne 0) { throw "cdim merge" }

& $py scripts/build_showroom_meaning_topology_graph_slice_v1.py --max-nodes 128
if ($LASTEXITCODE -ne 0) { throw "topology 128" }

if (-not $SkipVpsSync) {
    $env:JEMAAI_VPS_RELOAD_NGINX = "1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_showroom_to_vps.ps1
    if ($LASTEXITCODE -ne 0) { throw "vps sync" }
}

& $py scripts/probe_mkmlife_magic_orb_live_v1.py
if ($LASTEXITCODE -ne 0) { throw "mkmlife probe" }
& $py scripts/build_logos_phase12_live_bundle_v1.py
& $py scripts/build_logos_phase14_full_sweep_report_v1.py
if ($LASTEXITCODE -ne 0) { throw "sweep report" }
& $py scripts/build_logos_100pct_closure_v1.py --run-pytest --strict
if ($LASTEXITCODE -ne 0) { throw "closure" }

Write-Host "==> Phase14 full sweep done" -ForegroundColor Green
