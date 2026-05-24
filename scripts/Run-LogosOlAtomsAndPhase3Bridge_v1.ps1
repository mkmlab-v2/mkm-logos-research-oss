# Phase3: OL atoms health + LLM-plan bridge #3 + registry + router + CDIM + closure
param(
    [switch]$SkipAtomsHealth,
    [switch]$SkipBridge3,
    [switch]$BtrackOperatorProxyAck,
    [switch]$SkipClosure,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> LOGOS Phase3: OL atoms + bridge #3" -ForegroundColor Cyan

if (-not $SkipAtomsHealth) {
    & $py scripts/check_master_atoms_health.py
    if ($LASTEXITCODE -ne 0) { throw "master atoms health failed" }
}

if (-not $SkipBridge3) {
    & $py scripts/build_logos_concept_bridge_cloud_resilience_poc_v1.py
    if ($LASTEXITCODE -ne 0) { throw "cloud resilience bridge failed" }
}

& $py scripts/build_logos_concept_bridge_registry_v1.py `
    --bridge-json docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json `
    --bridge-json docs/final/artifacts/logos_concept_bridge_covenant_crisis_poc_v1_latest.json `
    --bridge-json docs/final/artifacts/logos_concept_bridge_cloud_resilience_poc_v1_latest.json
if ($LASTEXITCODE -ne 0) { throw "registry failed" }

if ($BtrackOperatorProxyAck) {
    & $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --btrack-operator-proxy-ack
    if ($LASTEXITCODE -ne 0) { throw "signoff failed" }
    & $py scripts/build_logos_concept_bridge_registry_v1.py `
        --bridge-json docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json `
        --bridge-json docs/final/artifacts/logos_concept_bridge_covenant_crisis_poc_v1_latest.json `
        --bridge-json docs/final/artifacts/logos_concept_bridge_cloud_resilience_poc_v1_latest.json
}

& $py scripts/run_logos_subgraph_graphrag_router_v1.py --query-id q01 --top-bridges 3
if ($LASTEXITCODE -ne 0) { throw "router q01 failed" }

& $py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
if ($LASTEXITCODE -ne 0) { throw "cdim failed" }

if (-not $SkipClosure) {
    & $py scripts/build_logos_100pct_closure_v1.py --run-pytest
    if ($LASTEXITCODE -ne 0) { throw "closure failed" }
}

Write-Host "==> Phase3 done" -ForegroundColor Green
