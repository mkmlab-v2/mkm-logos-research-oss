# q08 single insight chain — CPU ANN (no GPU contention with Nemotron WSL).
param(
    [switch]$SkipAnnLite,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

# Force sentence-transformers / torch off discrete GPU for this lane.
$env:CUDA_VISIBLE_DEVICES = ""
if (-not $env:MKM_LOGOS_ANN_LITE_ST_MODEL) {
    $env:MKM_LOGOS_ANN_LITE_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
}

$args = @(
    "scripts/run_magic_orb_question_insight_batch_v1.py",
    "--query-ids", "q08",
    "--expand-graph",
    "--sync-public-by-query"
)
if (-not $SkipAnnLite) {
    $args += "--include-ann-lite"
    $args += "--typology-boost"
}
if ($DryRun) { $args += "--dry-run" }

Write-Host "[q08] CPU-only ANN lane (CUDA_VISIBLE_DEVICES cleared)" -ForegroundColor Cyan
& py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $DryRun) {
    & py scripts/build_logos_gold_query_eval_report_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[OK] q08 insight + gold eval (CPU lane)" -ForegroundColor Green
