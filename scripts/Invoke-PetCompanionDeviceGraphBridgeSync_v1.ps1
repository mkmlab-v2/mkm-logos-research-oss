# P4: device_memory_bridge hints -> local graph slice -> registry refresh -> router smoke.
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> P4 Pet device graph bridge sync" -ForegroundColor Cyan

& $py scripts/apply_pet_companion_bridge_hints_to_local_graph_v1.py
if ($LASTEXITCODE -ne 0) { throw "apply bridge hints" }

& $py scripts/build_pet_companion_observation_bridge_registry_v1.py
if ($LASTEXITCODE -ne 0) { throw "observation registry" }

& $py scripts/run_pet_companion_subgraph_router_v1.py --scenario-id health_demo_01 `
    --output-json reports/pet_subgraph_replay/pet_router_after_bridge_sync.json
if ($LASTEXITCODE -ne 0) { throw "router smoke" }

& $py -m pytest tests/test_apply_pet_companion_bridge_hints_to_local_graph_v1.py -q --tb=short
if ($LASTEXITCODE -ne 0) { throw "pytest" }

Write-Host "==> P4 device graph bridge sync complete" -ForegroundColor Green
exit 0
