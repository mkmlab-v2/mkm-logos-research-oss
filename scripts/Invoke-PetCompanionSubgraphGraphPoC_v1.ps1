# Pet companion subgraph Graph PoC — registry + capped slice + router replay + recall eval.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$TopBridges = 2,
    [switch]$SkipRecallEval
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> P3 Pet subgraph PoC" -ForegroundColor Cyan

& $py scripts/build_pet_companion_observation_bridge_registry_v1.py
if ($LASTEXITCODE -ne 0) { throw "observation bridge registry" }

& $py scripts/build_pet_companion_local_graph_slice_v1.py --max-nodes 128 --max-edges 140
if ($LASTEXITCODE -ne 0) { throw "local graph slice" }

$scenarioIds = @("walk_demo_01", "health_demo_01", "safety_demo_01")

$outDir = Join-Path $WorkspaceRoot "reports/pet_subgraph_replay"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$rows = @()
$allPass = $true

foreach ($sid in $scenarioIds) {
    $relOut = "reports/pet_subgraph_replay/pet_router_replay_$sid.json"
    & $py scripts/run_pet_companion_subgraph_router_v1.py --scenario-id $sid --output-json $relOut --top-bridges $TopBridges
    $exit = $LASTEXITCODE
    $full = Join-Path $WorkspaceRoot $relOut
    $rowPass = $false
    $bridges = 0
    $pathsCount = 0
    if ($exit -eq 0 -and (Test-Path -LiteralPath $full)) {
        $doc = Get-Content -LiteralPath $full -Raw -Encoding UTF8 | ConvertFrom-Json
        $bridges = [int]$doc.bridges_matched
        $pathsCount = @($doc.paths).Count
        $rowPass = ($doc.hypothesis_tier -eq "B" -and $doc.non_gating -eq $true -and $bridges -ge 1 -and $pathsCount -ge 1)
    }
    if (-not $rowPass) { $allPass = $false }
    Write-Host ("  {0} pass={1} bridges={2} paths={3}" -f $sid, $rowPass, $bridges, $pathsCount) -ForegroundColor $(if ($rowPass) { "Green" } else { "Red" })
    $rows += [ordered]@{
        scenario_id     = $sid
        exit_code       = $exit
        bridges_matched = $bridges
        paths_count     = $pathsCount
        pass            = $rowPass
        out_json        = $relOut
    }
}

$summary = [ordered]@{
    schema           = "pet_companion_subgraph_replay_summary_v1"
    version          = "1.0.0"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hypothesis_tier  = "B"
    research_only    = $true
    non_gating       = $true
    pass             = $allPass
    pass_count       = @($rows | Where-Object { $_.pass }).Count
    query_count      = $rows.Count
    rows             = $rows
}
$summaryPath = Join-Path $WorkspaceRoot "reports/pet_companion_subgraph_replay_summary_latest.json"
($summary | ConvertTo-Json -Depth 8) + "`n" | Set-Content -LiteralPath $summaryPath -Encoding UTF8

if (-not $SkipRecallEval) {
    & $py scripts/eval_pet_companion_memory_recall_v1.py
    if ($LASTEXITCODE -ne 0) { Write-Host "recall eval non-zero (continuing PoC summary)" -ForegroundColor Yellow }
}

Write-Host "==> pet summary pass=$allPass ($($summary.pass_count)/$($summary.query_count))" -ForegroundColor $(if ($allPass) { "Green" } else { "Red" })
if (-not $allPass) { exit 1 }
exit 0
