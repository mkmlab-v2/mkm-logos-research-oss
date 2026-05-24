# Phase7: Gemini bridge #6 (mercy/q03) + signoff + router/CDIM + smoke + closure (VPS optional)
param(
    [switch]$DryRunGemini,
    [switch]$SkipVpsSync,
    [switch]$DryRunVpsSync,
    [switch]$SkipNginxReload,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$bridges = @(
    "docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_covenant_crisis_poc_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_cloud_resilience_poc_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_digital_trust_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_regime_watchfulness_gemini_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_mercy_compassion_gemini_v1_latest.json"
)

Write-Host "==> Phase7: Gemini bridge #6 (mercy / q03)" -ForegroundColor Cyan
$geminiArgs = @("scripts/build_logos_concept_bridge_mercy_compassion_gemini_v1.py")
if ($DryRunGemini) {
    $geminiArgs = @(
        "scripts/build_logos_concept_bridge_gemini_v1.py",
        "--concept-ko", "혼란과 상실 이후의 긍휴와 자비",
        "--concept-id", "concept:mercy_after_turmoil",
        "--output-json", "docs/final/artifacts/logos_concept_bridge_mercy_compassion_gemini_v1_latest.json",
        "--dry-run"
    )
}
& $py @geminiArgs
if ($LASTEXITCODE -ne 0) { throw "bridge #6 failed" }

$regArgs = @("scripts/build_logos_concept_bridge_registry_v1.py")
foreach ($b in $bridges) { $regArgs += @("--bridge-json", $b) }
& $py @regArgs
if ($LASTEXITCODE -ne 0) { throw "registry failed" }

Write-Host "==> commander signoff refresh" -ForegroundColor Cyan
& $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --commander-direct-signoff
if ($LASTEXITCODE -ne 0) { throw "bridge signoff failed" }
& $py @regArgs

Write-Host "==> q01 lock + RAG gate" -ForegroundColor Cyan
& $py scripts/apply_logos_rag_q01_theology_primary_order_v1.py
& $py scripts/run_logos_rag_dual_gold_eval_v1.py
& $py scripts/check_logos_rag_btrack_promotion_gate_v1.py
if ($LASTEXITCODE -ne 0) { throw "promotion gate failed" }

Write-Host "==> GraphRAG router q03 + CDIM" -ForegroundColor Cyan
& $py scripts/run_logos_subgraph_graphrag_router_v1.py --query-id q03 --top-bridges 6
if ($LASTEXITCODE -ne 0) { throw "router q03 failed" }
& $py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
if ($LASTEXITCODE -ne 0) { throw "cdim failed" }

& $py scripts/build_showroom_meaning_topology_graph_slice_v1.py --max-nodes 128
& $py scripts/build_logos_100pct_closure_v1.py --run-pytest
if ($LASTEXITCODE -ne 0) { throw "closure failed" }

Write-Host "==> showroom smoke" -ForegroundColor Cyan
& $py scripts/check_showroom_trust_viz_public_chain_v1.py
if ($LASTEXITCODE -ne 0) { throw "showroom smoke failed" }
& $py scripts/build_logos_observatory_commercial_readiness_v1.py

if (-not $SkipVpsSync) {
    Write-Host "==> VPS sync (NO RefreshStaging)" -ForegroundColor Cyan
    if (-not $SkipNginxReload) { $env:JEMAAI_VPS_RELOAD_NGINX = "1" }
    $syncArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\sync_showroom_to_vps.ps1")
    if ($DryRunVpsSync) { $syncArgs += "-DryRun" }
    if (Get-Command pwsh -ErrorAction SilentlyContinue) { & pwsh @syncArgs } else { & powershell.exe @syncArgs }
    if ($LASTEXITCODE -ne 0) { throw "vps sync failed" }
}

Write-Host "==> Phase7 done" -ForegroundColor Green
