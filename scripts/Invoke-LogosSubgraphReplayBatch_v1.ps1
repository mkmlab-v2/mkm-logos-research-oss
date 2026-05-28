# Logos subgraph GraphRAG router — q01-q12 bridge replay batch ([HYPO], NON_GATING).
# PASS = exit 0 per row + bridges_matched>=1 + paths_count>=1 + tier B + non_gating.
# NOT prophecy hit_rate; NOT Track A merge.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$GoldJson = "docs/final/artifacts/logos_semantic_query_gold_human_v1.json",
    [string]$RegistryJson = "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
    [string]$OutDir = "reports/subgraph_replay",
    [string]$SummaryJson = "reports/subgraph_router_replay_summary_latest.json",
    [int]$TopBridges = 2,
    [switch]$DryRun,
    [switch]$SkipGoldRestore
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$goldPath = Join-Path $WorkspaceRoot $GoldJson
$regPath = Join-Path $WorkspaceRoot $RegistryJson
$archiveGold = Join-Path $WorkspaceRoot "docs/final/artifacts/archive/cataloged/20260524T163333Z/docs/final/artifacts/logos_semantic_query_gold_human_v1.json"

if (-not $SkipGoldRestore -and -not (Test-Path -LiteralPath $goldPath) -and (Test-Path -LiteralPath $archiveGold)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $goldPath) | Out-Null
    Copy-Item -LiteralPath $archiveGold -Destination $goldPath -Force
    Write-Host "==> restored gold: $GoldJson" -ForegroundColor Yellow
}

function Test-Preflight {
    if (-not (Test-Path -LiteralPath $goldPath)) {
        throw "missing gold JSON: $GoldJson (run bootstrap_logos_query_gold_human_v1.py or restore archive)"
    }
    if (-not (Test-Path -LiteralPath $regPath)) {
        throw "missing registry: $RegistryJson (run build_logos_concept_bridge_registry_v1.py)"
    }
    $goldDoc = Get-Content -LiteralPath $goldPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $goldDoc.items) { throw "gold JSON has no items[]" }
    return @($goldDoc.items | ForEach-Object { [string]$_.id })
}

$ids = @(Test-Preflight)
$expected = @("q01", "q02", "q03", "q04", "q05", "q06", "q07", "q08", "q09", "q10", "q11", "q12")
$missingIds = @($expected | Where-Object { $_ -notin $ids })
if ($missingIds.Count -gt 0) {
    throw "gold missing query ids: $($missingIds -join ', ')"
}

$outRoot = Join-Path $WorkspaceRoot $OutDir
$summaryPath = Join-Path $WorkspaceRoot $SummaryJson
if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
}

$rows = @()
$allPass = $true
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

Write-Host "==> Logos subgraph replay batch ($($ids.Count) queries, top-bridges=$TopBridges)" -ForegroundColor Cyan

foreach ($qid in $expected) {
    $outFile = Join-Path $outRoot "subgraph_router_replay_$qid.json"
    $relOut = "$OutDir/subgraph_router_replay_$qid.json"
    if ($DryRun) {
        Write-Host "[dry-run] $py scripts/run_logos_subgraph_graphrag_router_v1.py --query-id $qid --output-json $relOut"
        continue
    }

    $routerArgs = @(
        "scripts/run_logos_subgraph_graphrag_router_v1.py",
        "--query-id", $qid,
        "--gold-json", $GoldJson,
        "--registry-json", $RegistryJson,
        "--output-json", $relOut,
        "--top-bridges", "$TopBridges"
    )
    & $py @routerArgs
    $exit = $LASTEXITCODE
    $rowPass = $false
    $bridges = 0
    $pathsCount = 0
    $err = ""

    if ($exit -eq 0 -and (Test-Path -LiteralPath $outFile)) {
        try {
            $doc = Get-Content -LiteralPath $outFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $bridges = [int]$doc.bridges_matched
            $pathsCount = @($doc.paths).Count
            $tierOk = ([string]$doc.hypothesis_tier -eq "B")
            $ngOk = ($doc.non_gating -eq $true)
            $rowPass = ($tierOk -and $ngOk -and $bridges -ge 1 -and $pathsCount -ge 1)
            if (-not $rowPass) {
                $err = "validation: tier=$($doc.hypothesis_tier) non_gating=$($doc.non_gating) bridges=$bridges paths=$pathsCount"
            }
        } catch {
            $err = "parse error: $_"
        }
    } else {
        $err = if ($exit -ne 0) { "router exit $exit" } else { "missing output $relOut" }
    }

    if (-not $rowPass) { $allPass = $false }
    $color = if ($rowPass) { "Green" } else { "Red" }
    Write-Host ("  {0} exit={1} bridges={2} paths={3} pass={4} {5}" -f $qid, $exit, $bridges, $pathsCount, $rowPass, $err) -ForegroundColor $color

    $rows += [ordered]@{
        query_id       = $qid
        exit_code      = $exit
        bridges_matched = $bridges
        paths_count    = $pathsCount
        pass           = $rowPass
        out_json       = $relOut
        error          = $err
    }
}

if ($DryRun) {
    Write-Host "==> dry-run complete (no router invocations)" -ForegroundColor Yellow
    exit 0
}

$summary = [ordered]@{
    schema             = "logos_subgraph_router_replay_summary_v1"
    version            = "1.0.0"
    generated_at_utc   = $utc
    hypothesis_tier    = "B"
    research_only      = $true
    non_gating         = $true
    pass               = $allPass
    query_count        = $rows.Count
    pass_count         = @($rows | Where-Object { $_.pass }).Count
    top_bridges        = $TopBridges
    gold_json          = $GoldJson
    registry_json      = $RegistryJson
    rows               = $rows
    policy             = [ordered]@{
        no_prophecy_hit_rate_claim = $true
        no_track_a_merge           = $true
        router_kind                = "token_overlap_logos_subgraph_v1"
        global_atom_network_merge  = $false
    }
}

$summaryDir = Split-Path -Parent $summaryPath
if ($summaryDir) { New-Item -ItemType Directory -Force -Path $summaryDir | Out-Null }
($summary | ConvertTo-Json -Depth 8) + "`n" | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host "==> summary: $SummaryJson pass=$allPass ($($summary.pass_count)/$($summary.query_count))" -ForegroundColor $(if ($allPass) { "Green" } else { "Red" })
if (-not $allPass) { exit 1 }
exit 0
