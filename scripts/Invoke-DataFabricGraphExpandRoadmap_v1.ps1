# Graph expand roadmap: run batches until target node count (default 3000)
param(
    [int]$TargetNodes = 3000,
    [int]$BatchSize = 500,
    [int]$MaxBatches = 8
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$nodesPath = "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
$steps = @()
$batch = 0

function Get-NodeLineCount {
    if (-not (Test-Path $nodesPath)) { return 0 }
    return (Get-Content $nodesPath | Where-Object { $_.Trim() }).Count
}

$start = Get-NodeLineCount
Write-Host "roadmap start nodes=$start target=$TargetNodes batch=$BatchSize" -ForegroundColor Cyan

while ((Get-NodeLineCount) -lt $TargetNodes -and $batch -lt $MaxBatches) {
    $batch++
    $before = Get-NodeLineCount
    Write-Host "== expand batch $batch (before=$before) ==" -ForegroundColor Cyan
    py scripts/run_logos_graph_expand_batch_v1.py --batch-size $BatchSize
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $after = Get-NodeLineCount
    $steps += [ordered]@{ batch = $batch; nodes_before = $before; nodes_after = $after }
    if ($after -le $before) {
        Write-Host "warn: no growth; stopping" -ForegroundColor DarkYellow
        break
    }
}

$end = Get-NodeLineCount
$report = @{
    schema = "logos_graph_expand_roadmap_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    target_nodes = $TargetNodes
    batch_size = $BatchSize
    nodes_start = $start
    nodes_end = $end
    target_reached = ($end -ge $TargetNodes)
    steps = $steps
}
$out = "docs/final/artifacts/logos_graph_expand_roadmap_v1_latest.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -Path $out -Encoding utf8
Write-Host "Wrote $out nodes=$end" -ForegroundColor Green
if ($end -lt $TargetNodes) { exit 2 }
exit 0
