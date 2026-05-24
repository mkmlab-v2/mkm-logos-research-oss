# Golden 40 expansion dry-run (B-track). Does not write ACTIVE report or Golden input SSOT.
param(
    [string]$TargetCounts = "40,80,120,200",
    [ValidateSet("mixed_matrix", "homogeneous_sasang_ko", "golden_core_only")]
    [string]$PoolMode = "mixed_matrix",
    [switch]$PlanOnly,
    [switch]$ComparePools,
    [switch]$FullEval
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($ComparePools) {
    $cmpArgs = @("scripts/run_golden40_expansion_pool_compare_v1.py", "--target-counts", $TargetCounts)
    if ($PlanOnly -and -not $FullEval) { $cmpArgs += "--plan-only" }
    & py @cmpArgs
    exit $LASTEXITCODE
}

$pyArgs = @(
    "scripts/run_golden40_expansion_dryrun_v1.py",
    "--target-counts", $TargetCounts,
    "--pool-mode", $PoolMode
)
if ($PlanOnly -and -not $FullEval) {
    $pyArgs += "--plan-only"
}

& py @pyArgs
exit $LASTEXITCODE
