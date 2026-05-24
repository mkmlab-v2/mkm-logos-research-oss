# Phase9: bridges #8-14 for gold q02,q05-q07,q09-q12 + full registry + closure
param(
    [switch]$TemplateOnly,
    [switch]$SkipVpsSync,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$batchIds = @("q02", "q05", "q06", "q07", "q09", "q10", "q11", "q12")

Write-Host "==> Phase9: batch gold bridges ($($batchIds -join ','))" -ForegroundColor Cyan
foreach ($qid in $batchIds) {
    $args = @("scripts/build_logos_concept_bridge_for_gold_query_v1.py", "--query-id", $qid)
    if ($TemplateOnly) { $args += "--template-only" }
    & $py @args
    if ($LASTEXITCODE -ne 0) { throw "bridge build failed: $qid" }
}

$bridges = @(
    "docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_covenant_crisis_poc_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_cloud_resilience_poc_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_digital_trust_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_regime_watchfulness_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_mercy_compassion_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_wisdom_uncertainty_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_gold_q02_judgment_warning_collapse_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_gold_q05_hope_prolonged_stress_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_gold_q06_discipline_in_volatility_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_gold_q07_restoration_after_disruption_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_gold_q09_prudence_liquidity_stress_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_gold_q10_resilience_capitulation_phase_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_gold_q11_stability_after_volatility_shock_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_gold_q12_risk_excess_cycle_unwind_gemini_v1_latest.json"
)

$regArgs = @("scripts/build_logos_concept_bridge_registry_v1.py")
foreach ($b in $bridges) { $regArgs += @("--bridge-json", $b) }
& $py @regArgs
if ($LASTEXITCODE -ne 0) { throw "registry" }

& $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --commander-direct-signoff
& $py @regArgs

& $py scripts/apply_logos_rag_q01_theology_primary_order_v1.py
& $py scripts/run_logos_rag_dual_gold_eval_v1.py
& $py scripts/check_logos_rag_btrack_promotion_gate_v1.py
if ($LASTEXITCODE -ne 0) { throw "gate" }

Write-Host "==> routers (sample q01,q05,q11)" -ForegroundColor Cyan
foreach ($rid in @("q01", "q05", "q11")) {
    & $py scripts/run_logos_subgraph_graphrag_router_v1.py --query-id $rid --top-bridges 15
    if ($LASTEXITCODE -ne 0) { throw "router $rid" }
}

& $py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
& $py scripts/build_showroom_meaning_topology_graph_slice_v1.py --max-nodes 128
& $py scripts/build_logos_100pct_closure_v1.py --run-pytest
if ($LASTEXITCODE -ne 0) { throw "closure" }

& $py scripts/check_showroom_trust_viz_public_chain_v1.py
& $py scripts/build_logos_observatory_commercial_readiness_v1.py

if (-not $SkipVpsSync) {
    $env:JEMAAI_VPS_RELOAD_NGINX = "1"
    if (Get-Command pwsh -ErrorAction SilentlyContinue) {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\sync_showroom_to_vps.ps1
    } else {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\sync_showroom_to_vps.ps1
    }
}

Write-Host "==> Phase9 batch done (bridge_count=15)" -ForegroundColor Green
