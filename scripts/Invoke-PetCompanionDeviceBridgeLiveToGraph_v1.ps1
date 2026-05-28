# P5: Live Worker device_memory_bridge -> local graph slice -> registry -> router smoke.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$BaseUrl = "",
    [switch]$DryRunFetch,
    [switch]$FallbackFixtureOnBlock,
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> P5 Pet device bridge LIVE -> graph" -ForegroundColor Cyan

$fetchArgs = @("scripts/fetch_pet_companion_device_bridge_live_v1.py")
if ($BaseUrl) { $fetchArgs += @("--base-url", $BaseUrl) }
if ($DryRunFetch) { $fetchArgs += "--dry-run" }
if ($FallbackFixtureOnBlock) { $fetchArgs += "--fallback-fixture-on-block" }

& $py @fetchArgs
if ($LASTEXITCODE -ne 0) { throw "live bridge fetch" }

if ($DryRunFetch) {
    Write-Host "==> dry-run fetch only; stopping before graph apply" -ForegroundColor Yellow
    exit 0
}

& $py scripts/apply_pet_companion_bridge_hints_to_local_graph_v1.py `
    --response-json reports/pet_companion_device_bridge_live_response_latest.json `
    --request-json reports/pet_companion_device_bridge_live_request_latest.json
if ($LASTEXITCODE -ne 0) { throw "apply live bridge hints" }

& $py scripts/build_pet_companion_observation_bridge_registry_v1.py
if ($LASTEXITCODE -ne 0) { throw "observation registry" }

& $py scripts/run_pet_companion_subgraph_router_v1.py --scenario-id health_demo_01 `
    --output-json reports/pet_subgraph_replay/pet_router_after_live_bridge.json
if ($LASTEXITCODE -ne 0) { throw "router smoke after live bridge" }

if (-not $SkipPytest) {
    & $py -m pytest tests/test_fetch_pet_companion_device_bridge_live_v1.py tests/test_apply_pet_companion_bridge_hints_to_local_graph_v1.py -q --tb=short
    if ($LASTEXITCODE -ne 0) { throw "pytest" }
}

Write-Host "==> P5 live bridge -> graph complete" -ForegroundColor Green
exit 0
