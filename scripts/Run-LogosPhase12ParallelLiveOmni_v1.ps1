# Phase12 parallel: live showroom + RAG/L3 readiness + CDIM/wire + commercial/closure
param(
    [switch]$SkipLiveProbe,
    [switch]$SkipOmniCdim,
    [switch]$SkipClosurePytest,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$trackLive = {
    Set-Location $using:WorkspaceRoot
    $py = $using:py
    & $py scripts/check_showroom_trust_viz_public_chain_v1.py
    if ($LASTEXITCODE -ne 0) { throw "showroom smoke" }
    & $py scripts/build_logos_phase12_live_bundle_v1.py
    if ($LASTEXITCODE -ne 0) { throw "phase12 live bundle" }
    & $py scripts/build_showroom_static_load_probe_v1.py --requests-per-url 5 --workers 6
    if ($LASTEXITCODE -ne 0) { throw "load probe" }
}

$trackRag = {
    Set-Location $using:WorkspaceRoot
    $py = $using:py
    & $py scripts/apply_logos_rag_q01_theology_primary_order_v1.py
    if ($LASTEXITCODE -ne 0) { throw "q01 order" }
    & $py scripts/run_logos_rag_dual_gold_eval_v1.py
    if ($LASTEXITCODE -ne 0) { throw "dual eval" }
    & $py scripts/build_logos_rag_l3_readiness_v1.py
    if ($LASTEXITCODE -ne 0) { throw "l3 readiness" }
    & $py scripts/check_logos_rag_btrack_promotion_gate_v1.py
    if ($LASTEXITCODE -ne 0) { throw "promotion gate" }
}

$trackGraph = {
    Set-Location $using:WorkspaceRoot
    $py = $using:py
    & $py scripts/build_logos_graph_wire_profile_v1.py
    if ($LASTEXITCODE -ne 0) { throw "wire profile" }
    & $py scripts/build_mkm_graph_wire_rag_poc_v1.py
    if ($LASTEXITCODE -ne 0) { throw "wire poc" }
    & $py scripts/build_logos_concept_bridge_registry_v1.py
    if ($LASTEXITCODE -ne 0) { throw "bridge registry" }
}

$trackOps = {
    Set-Location $using:WorkspaceRoot
    $py = $using:py
    & $py scripts/build_logos_observatory_commercial_readiness_v1.py
    if ($LASTEXITCODE -ne 0) { throw "commercial readiness" }
}

$jobs = @()
if (-not $SkipLiveProbe) { $jobs += Start-Job -Name LiveShowroom -ScriptBlock $trackLive }
$jobs += Start-Job -Name RagL3 -ScriptBlock $trackRag
if (-not $SkipOmniCdim) { $jobs += Start-Job -Name GraphCdim -ScriptBlock $trackGraph }
$jobs += Start-Job -Name OpsCommercial -ScriptBlock $trackOps

Write-Host "==> Phase12 parallel: $($jobs.Count) tracks" -ForegroundColor Cyan
$jobs | Wait-Job | Out-Null
foreach ($j in $jobs) {
    if ($j.State -eq "Failed") {
        Receive-Job -Job $j -ErrorAction SilentlyContinue | Write-Host
        throw "Parallel track $($j.Name) failed"
    }
    Write-Host "--- $($j.Name) ---" -ForegroundColor DarkCyan
    Receive-Job -Job $j | Write-Host
    Remove-Job -Job $j
}

Write-Host "==> Phase12 merge: signoff + CDIM + showroom slice + envelope + closure" -ForegroundColor Cyan
& $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --commander-direct-signoff
if ($LASTEXITCODE -ne 0) { throw "bridge signoff" }
& $py scripts/build_logos_concept_bridge_registry_v1.py
if ($LASTEXITCODE -ne 0) { throw "bridge registry" }
if (-not $SkipOmniCdim) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-LogosCrossDomainInterfaceParallel_v1.ps1 -SkipLens -Validate
    if ($LASTEXITCODE -ne 0) { throw "cdim" }
}
& $py scripts/build_showroom_cdim_slice_v1.py
if ($LASTEXITCODE -ne 0) { throw "cdim slice" }
& $py scripts/build_mkm_trackc_ops_dashboard_v1.py
if ($LASTEXITCODE -ne 0) { throw "trackc dashboard" }
& $py scripts/assemble_three_lens_sphere_envelope_v1.py --validate-schema --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { throw "envelope" }
& $py scripts/build_logos_4rag_envelope_refresh_report_v1.py
if ($LASTEXITCODE -ne 0) { throw "4rag report" }
if ($SkipClosurePytest) {
    & $py scripts/build_logos_100pct_closure_v1.py --strict
} else {
    & $py scripts/build_logos_100pct_closure_v1.py --run-pytest --strict
}
if ($LASTEXITCODE -ne 0) { throw "closure" }

Write-Host "==> Phase12 parallel complete" -ForegroundColor Green
