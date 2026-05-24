# Phase5 parallel: q01 theology pack + RAG eval refresh + envelope/CDIM + smoke + closure + optional VPS nginx reload
param(
    [switch]$SkipVpsSync,
    [switch]$SkipNginxReload,
    [switch]$DryRunVpsSync,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> LOGOS-100PCT Phase5 parallel" -ForegroundColor Cyan

$jobs = @(
    @{
        Name = "theology_q01"
        Block = {
            param($Root, $Py)
            Set-Location $Root
            & $Py scripts/build_logos_rag_q01_theology_adjudication_v1.py
            if ($LASTEXITCODE -ne 0) { throw "theology q01" }
            & $Py scripts/export_logos_rag_provisional_thematic_review_v1.py
            if ($LASTEXITCODE -ne 0) { throw "provisional export" }
        }
    }
    @{
        Name = "rag_eval_refresh"
        Block = {
            param($Root, $Py)
            Set-Location $Root
            & $Py scripts/apply_logos_rag_thematic_union_retrieval_top1_v1.py
            if ($LASTEXITCODE -ne 0) { throw "union" }
            & $Py scripts/apply_logos_rag_thematic_harness_align_v1.py
            if ($LASTEXITCODE -ne 0) { throw "harness align" }
            & $Py scripts/run_logos_rag_dual_gold_eval_v1.py
            if ($LASTEXITCODE -ne 0) { throw "dual eval" }
            & $Py scripts/check_logos_rag_btrack_promotion_gate_v1.py
            if ($LASTEXITCODE -ne 0) { throw "promotion gate" }
        }
    }
    @{
        Name = "envelope_ops"
        Block = {
            param($Root, $Py)
            Set-Location $Root
            & $Py scripts/assemble_three_lens_sphere_envelope_v1.py --validate-schema
            if ($LASTEXITCODE -ne 0) { throw "envelope" }
            if (Test-Path "$Root/scripts/build_logos_observatory_commercial_readiness_v1.py") {
                & $Py scripts/build_logos_observatory_commercial_readiness_v1.py
                if ($LASTEXITCODE -ne 0) { throw "commercial readiness" }
            }
        }
    }
    @{
        Name = "showroom_smoke"
        Block = {
            param($Root, $Py)
            Set-Location $Root
            if (Test-Path "$Root/scripts/check_showroom_trust_viz_public_chain_v1.py") {
                & $Py scripts/check_showroom_trust_viz_public_chain_v1.py
                if ($LASTEXITCODE -ne 0) { throw "showroom smoke" }
            }
        }
    }
)

$started = foreach ($spec in $jobs) {
    Start-Job -Name $spec.Name -ScriptBlock $spec.Block -ArgumentList $WorkspaceRoot, $py
}
Wait-Job -Job $started | Out-Null
foreach ($j in $started) {
    if ($j.State -ne "Completed") {
        Receive-Job -Job $j -ErrorAction SilentlyContinue | Write-Host
        throw "Job $($j.Name) failed: $($j.State)"
    }
    Receive-Job -Job $j | Write-Host
    Remove-Job -Job $j
}

Write-Host "==> sequential: router + CDIM + topology + closure" -ForegroundColor Cyan
& $py scripts/run_logos_subgraph_graphrag_router_v1.py --query-id q01 --top-bridges 4
if ($LASTEXITCODE -ne 0) { throw "router" }

& $py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
if ($LASTEXITCODE -ne 0) { throw "cdim" }

& $py scripts/build_showroom_meaning_topology_graph_slice_v1.py --max-nodes 128
if ($LASTEXITCODE -ne 0) { throw "topology" }

& $py scripts/build_logos_100pct_closure_v1.py --run-pytest
if ($LASTEXITCODE -ne 0) { throw "closure" }

if (-not $SkipVpsSync) {
    Write-Host "==> VPS sync (no RefreshStaging)" -ForegroundColor Cyan
    if (-not $SkipNginxReload) {
        $env:JEMAAI_VPS_RELOAD_NGINX = "1"
    }
    $syncArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\sync_showroom_to_vps.ps1")
    if ($DryRunVpsSync) { $syncArgs += "-DryRun" }
    if (Get-Command pwsh -ErrorAction SilentlyContinue) {
        & pwsh @syncArgs
    } else {
        & powershell.exe @syncArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "vps sync exit $LASTEXITCODE" }
}

Write-Host "==> Phase5 done" -ForegroundColor Green
