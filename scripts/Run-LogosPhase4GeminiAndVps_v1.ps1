# Phase4: Gemini concept_bridge #4 + registry + router/CDIM + topology guard + VPS sync (no RefreshStaging)
param(
    [switch]$DryRunGemini,
    [switch]$DryRunVpsSync,
    [switch]$SkipVpsSync,
    [switch]$BtrackOperatorProxyAck,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$bridges = @(
    "docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_covenant_crisis_poc_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_cloud_resilience_poc_v1_latest.json",
    "docs/final/artifacts/logos_concept_bridge_digital_trust_gemini_v1_latest.json"
)

Write-Host "==> Phase4: Gemini bridge #4" -ForegroundColor Cyan
$geminiArgs = @("scripts/build_logos_concept_bridge_gemini_v1.py")
if ($DryRunGemini) { $geminiArgs += "--dry-run" }
& $py @geminiArgs
if ($LASTEXITCODE -ne 0) { throw "gemini bridge failed" }

$regArgs = @("scripts/build_logos_concept_bridge_registry_v1.py")
foreach ($b in $bridges) { $regArgs += @("--bridge-json", $b) }
& $py @regArgs
if ($LASTEXITCODE -ne 0) { throw "registry failed" }

if ($BtrackOperatorProxyAck) {
    & $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --btrack-operator-proxy-ack
    if ($LASTEXITCODE -ne 0) { throw "signoff failed" }
    & $py @regArgs
}

& $py scripts/run_logos_subgraph_graphrag_router_v1.py --query-id q01 --top-bridges 4
if ($LASTEXITCODE -ne 0) { throw "router failed" }

& $py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
if ($LASTEXITCODE -ne 0) { throw "cdim failed" }

Write-Host "==> topology slice guard (128 nodes)" -ForegroundColor Cyan
& $py scripts/build_showroom_meaning_topology_graph_slice_v1.py --max-nodes 128
if ($LASTEXITCODE -ne 0) { throw "topology slice failed" }

& $py scripts/build_logos_100pct_closure_v1.py --run-pytest
if ($LASTEXITCODE -ne 0) { throw "closure failed" }

if (-not $SkipVpsSync) {
    Write-Host "==> VPS showroom sync (NO RefreshStaging)" -ForegroundColor Cyan
    $syncArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\sync_showroom_to_vps.ps1")
    if ($DryRunVpsSync) { $syncArgs += "-DryRun" }
    if (Get-Command pwsh -ErrorAction SilentlyContinue) {
        & pwsh @syncArgs
    } else {
        & powershell.exe @syncArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "vps sync failed exit $LASTEXITCODE" }
}

Write-Host "==> Phase4 done" -ForegroundColor Green
