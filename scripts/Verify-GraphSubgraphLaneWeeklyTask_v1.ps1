<#
.SYNOPSIS
  Verify MKM_GraphSubgraph_LaneWeekly scheduled task registration and latest replay summaries.
#>
param(
    [string]$TaskName = "MKM_GraphSubgraph_LaneWeekly",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "task_missing: $TaskName"
    exit 2
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "task_name=$TaskName state=$($task.State) last_result=$($info.LastTaskResult) next_run=$($info.NextRunTime)"

$logosSummary = Join-Path $root "reports\subgraph_router_replay_summary_latest.json"
$petSummary = Join-Path $root "reports\pet_companion_subgraph_replay_summary_latest.json"
$contract = Join-Path $root "docs\final\artifacts\graph_subgraph_router_lane_contract_v1_latest.json"

$ok = $true
foreach ($p in @($logosSummary, $petSummary, $contract)) {
    if (-not (Test-Path -LiteralPath $p)) {
        Write-Host "missing: $p"
        $ok = $false
        continue
    }
    $doc = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($p -like "*summary*") {
        $pass = [bool]$doc.pass
        Write-Host "$(Split-Path $p -Leaf) pass=$pass"
        if (-not $pass) { $ok = $false }
    } else {
        Write-Host "$(Split-Path $p -Leaf) schema=$($doc.schema)"
    }
}

if (-not $ok) { exit 1 }
exit 0
