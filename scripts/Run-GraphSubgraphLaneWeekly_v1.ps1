# Weekly Graph subgraph lane: refresh pet slots (best-effort) + full P2/P1/P3 chain.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$KvNamespaceId = "2dc41cddcb1e417181bd2876916697bd",
    [string]$KvPrefix = "pet_companion/coach_events/",
    [string]$WranglerCwd = "C:\workspace\projects\mkm\mkm-life",
    [int]$SlotDays = 30,
    [switch]$SkipSlotRefresh
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (-not $SkipSlotRefresh) {
    Write-Host "==> refresh pet memory slots (KV best-effort)" -ForegroundColor Cyan
    & $py scripts/build_pet_companion_memory_slots_v1.py `
        --kv-namespace-id $KvNamespaceId `
        --kv-prefix $KvPrefix `
        --wrangler-cwd $WranglerCwd `
        --days $SlotDays
    if ($LASTEXITCODE -ne 0) {
        Write-Host "slot refresh failed — continuing with existing reports/pet_companion_memory_slots_latest.json" -ForegroundColor Yellow
    }
}

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-GraphSubgraphLaneRecommendedChain_v1.ps1
if ($LASTEXITCODE -ne 0) { throw "GraphSubgraphLaneRecommendedChain exit $LASTEXITCODE" }

& $py scripts/build_graph_subgraph_lane_ops_status_v1.py
if ($LASTEXITCODE -ne 0) { throw "graph lane ops status" }

Write-Host "==> Graph subgraph weekly run complete" -ForegroundColor Green
exit 0
