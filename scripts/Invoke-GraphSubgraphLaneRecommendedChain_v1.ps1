# Recommended auto chain: P2 lane contract + P1 Logos replay + P3 Pet subgraph PoC.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipLogosReplay,
    [switch]$SkipPetPoC,
    [switch]$SkipDeviceGraphSync,
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> Graph subgraph lane recommended chain (P2+P1+P3)" -ForegroundColor Cyan

& $py scripts/build_graph_subgraph_router_lane_contract_v1.py
if ($LASTEXITCODE -ne 0) { throw "lane contract" }

if (-not $SkipLogosReplay) {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LogosSubgraphReplayBatch_v1.ps1
    if ($LASTEXITCODE -ne 0) { throw "logos replay batch" }
} else {
    Write-Host "==> skipped Logos replay (-SkipLogosReplay)" -ForegroundColor Yellow
}

if (-not $SkipPetPoC) {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PetCompanionSubgraphGraphPoC_v1.ps1
    if ($LASTEXITCODE -ne 0) { throw "pet subgraph PoC" }
} else {
    Write-Host "==> skipped Pet PoC (-SkipPetPoC)" -ForegroundColor Yellow
}

if (-not $SkipDeviceGraphSync) {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PetCompanionDeviceGraphBridgeSync_v1.ps1
    if ($LASTEXITCODE -ne 0) { throw "pet device graph sync (P4)" }
} else {
    Write-Host "==> skipped P4 device graph sync (-SkipDeviceGraphSync)" -ForegroundColor Yellow
}

if (-not $SkipPytest) {
    & $py -m pytest tests/test_graph_subgraph_router_lane_contract_v1.py tests/test_run_pet_companion_subgraph_router_v1.py tests/test_build_pet_companion_local_graph_slice_v1.py tests/test_apply_pet_companion_bridge_hints_to_local_graph_v1.py -q --tb=short
    if ($LASTEXITCODE -ne 0) { throw "pytest" }
}

Write-Host "==> Graph subgraph lane chain complete" -ForegroundColor Green
exit 0
