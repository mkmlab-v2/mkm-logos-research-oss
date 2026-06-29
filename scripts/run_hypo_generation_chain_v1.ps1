# Research Shadow Lane — hypo generation chain v1
# Track B only · [HYPO][NON_GATING] · Fact-Lock: no causal verdict merge

param(
    [string]$IssueId = "job_prologue_suffering",
    [string]$Query = "욥이 고난을 받은 이유",
    [string]$QueryId = "job_suffering_reason",
    [switch]$SkipRouter,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$SeedMap = @{
    "job_prologue_suffering" = "docs/final/artifacts/research_shadow_lane_seeds/job_prologue_suffering_v1.json"
}

if (-not $SeedMap.ContainsKey($IssueId)) {
    Write-Error "Unknown IssueId: $IssueId (known: $($SeedMap.Keys -join ', '))"
}

$Seed = Join-Path $Root $SeedMap[$IssueId]
$RouterOut = Join-Path $Root "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
$TreeOut = Join-Path $Root "docs/final/artifacts/research_shadow_lane_hypothesis_tree_v1_latest.json"

Write-Host "[shadow-lane] issue=$IssueId query=$Query"

if (-not $SkipRouter) {
    $routerCmd = @(
        "py", "scripts/run_question_semantic_rag_bridge_chain_v1.py",
        "--query", $Query,
        "--query-id", $QueryId,
        "--skip-ann-lite"
    )
    if ($DryRun) {
        Write-Host "[dry-run] $($routerCmd -join ' ')"
    } else {
        & $routerCmd[0] $routerCmd[1..($routerCmd.Length - 1)]
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

$buildCmd = @(
    "py", "scripts/build_research_shadow_lane_hypothesis_tree_v1.py",
    "--seed-json", $Seed,
    "--router-json", $RouterOut,
    "--query-id", $QueryId
)
if ($DryRun) {
    Write-Host "[dry-run] $($buildCmd -join ' ')"
    exit 0
}

& $buildCmd[0] $buildCmd[1..($buildCmd.Length - 1)]
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[shadow-lane] ok artifact=$TreeOut"
exit 0
