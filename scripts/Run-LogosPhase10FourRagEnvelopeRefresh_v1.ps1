# Phase10: 4RAG envelope full refresh chain + mkmlife copy + closure + optional VPS
param(
    [switch]$SkipOlAtoms,
    [switch]$SkipVpsSync,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> Phase10: 4RAG upstream refresh" -ForegroundColor Cyan
& $py scripts/report_independent_lens_fusion_stub_v0.py
if ($LASTEXITCODE -ne 0) { throw "fusion stub" }

& $py scripts/build_logos_graph_wire_profile_v1.py
& $py scripts/build_mkm_graph_wire_rag_poc_v1.py

& $py scripts/build_logos_concept_bridge_registry_v1.py
& $py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
if ($LASTEXITCODE -ne 0) { throw "cdim" }

& $py scripts/build_showroom_meaning_topology_graph_slice_v1.py --max-nodes 128
& $py scripts/apply_logos_rag_q01_theology_primary_order_v1.py
& $py scripts/run_logos_rag_dual_gold_eval_v1.py
& $py scripts/check_logos_rag_btrack_promotion_gate_v1.py
if ($LASTEXITCODE -ne 0) { throw "gate" }

if (-not $SkipOlAtoms) {
    $verse = Join-Path $WorkspaceRoot "data\logos\verse_decoded_v2.jsonl"
    if (Test-Path -LiteralPath $verse) {
        Write-Host "==> OL master atoms refresh" -ForegroundColor Cyan
        & $py scripts/core/build_original_language_master_atoms.py
        if ($LASTEXITCODE -ne 0) { throw "ol atoms" }
    }
}

Write-Host "==> assemble envelope + mkmlife copy" -ForegroundColor Cyan
& $py scripts/assemble_three_lens_sphere_envelope_v1.py --validate-schema --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { throw "envelope" }

& $py scripts/build_logos_4rag_envelope_refresh_report_v1.py
if ($LASTEXITCODE -ne 0) { throw "4rag report" }

& $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --commander-direct-signoff
if ($LASTEXITCODE -ne 0) { throw "bridge signoff" }
& $py scripts/build_logos_concept_bridge_registry_v1.py

& $py scripts/build_logos_100pct_closure_v1.py --run-pytest
if ($LASTEXITCODE -ne 0) { throw "closure" }

& $py scripts/build_logos_observatory_commercial_readiness_v1.py
& $py scripts/check_showroom_trust_viz_public_chain_v1.py
if ($LASTEXITCODE -ne 0) { throw "smoke" }

if (-not $SkipVpsSync) {
    $env:JEMAAI_VPS_RELOAD_NGINX = "1"
    if (Get-Command pwsh -ErrorAction SilentlyContinue) {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\sync_showroom_to_vps.ps1
    } else {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\sync_showroom_to_vps.ps1
    }
    if ($LASTEXITCODE -ne 0) { throw "vps sync" }
}

Write-Host "==> Phase10 4RAG envelope refresh done" -ForegroundColor Green
