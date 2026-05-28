# Daily commercial B-track ops: dual-runtime heartbeat + memory-graph task verify + graph lane status.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipMemoryGraphVerify,
    [switch]$SkipGraphLaneStatus
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> MKM commercial ops daily" -ForegroundColor Cyan

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmDualRuntimeHeartbeat_v1.ps1
if ($LASTEXITCODE -ne 0) { throw "dual runtime heartbeat" }

if (-not $SkipMemoryGraphVerify) {
    $mgVerify = Join-Path $WorkspaceRoot "scripts\Verify-MemoryGraphOpsDailyTask_v1.ps1"
    if (Test-Path -LiteralPath $mgVerify) {
        powershell -NoProfile -ExecutionPolicy Bypass -File $mgVerify
        if ($LASTEXITCODE -ne 0) { throw "memory graph ops daily verify" }
    }
}

if (-not $SkipGraphLaneStatus) {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-GraphSubgraphLaneWeeklyTask_v1.ps1
    if ($LASTEXITCODE -ne 0) { throw "graph subgraph weekly verify" }
    & $py scripts/build_graph_subgraph_lane_ops_status_v1.py
    if ($LASTEXITCODE -ne 0) { throw "graph lane ops status" }
}

Write-Host "==> commercial ops daily complete" -ForegroundColor Green
exit 0
