# Sync Logos Studio query-time GraphRAG artifacts + scripts to VPS monorepo.

param(
    [string]$Remote = "vps-mkmlife",
    [string]$MonorepoRoot = "/opt/mkm-destiny-ai-41e38ec6"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$remote = "${Remote}:${MonorepoRoot}"

$scripts = @(
    "encode_logos_studio_query_graphrag_v1.py",
    "export_showroom_qa_router_paths_v1.py",
    "compute_logos_reasoning_path_v1.py",
    "logos_verse_ref_canonical_v1.py",
    "logos_gematria_lexicon_router_lib_v1.py",
    "run_logos_subgraph_graphrag_router_v1.py",
    "build_logos_gold_query_eval_report_v1.py"
)

foreach ($s in $scripts) {
    & scp -o BatchMode=yes (Join-Path $root "scripts\$s") "${remote}/scripts/"
}

$artifacts = @(
    "logos_concept_bridge_registry_v1_latest.json",
    "logos_lemma_verse_edges_v1.jsonl",
    "logos_graph_seed_chain_v1_latest.json",
    "showroom_meaning_topology_graph_slice_v1_latest.json"
)

foreach ($a in $artifacts) {
    & scp -o BatchMode=yes (Join-Path $root "docs\final\artifacts\$a") "${remote}/docs/final/artifacts/"
}

Get-ChildItem (Join-Path $root "docs\final\artifacts") -Filter "logos_concept_bridge_*.json" | ForEach-Object {
    & scp -o BatchMode=yes $_.FullName "${remote}/docs/final/artifacts/"
}

$out = Join-Path $root "reports\logos_studio_graphrag_artifacts_sync_latest.json"
@{
    schema = "logos_studio_graphrag_artifacts_sync_v1"
    ok = $true
    remote = $Remote
    monorepo_root = $MonorepoRoot
    reproduce = "powershell -File scripts/Invoke-LogosStudioGraphragArtifactsSync_v1.ps1"
} | ConvertTo-Json | Set-Content -Path $out -Encoding UTF8
Write-Host "WROTE: $out"
