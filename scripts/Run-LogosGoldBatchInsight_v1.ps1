# q05–q08 (and optional) Magic Orb gold insight batch — CPU ANN + typology + 64 LOD bloom.
param(
    [string[]]$QueryIds = @("q05", "q06", "q07", "q08"),
    [switch]$SkipAnnLite,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

if ($QueryIds.Count -eq 1 -and $QueryIds[0] -match ',') {
    $QueryIds = $QueryIds[0].Split(',') | ForEach-Object { $_.Trim().Trim('"') } | Where-Object { $_ }
}
$QueryIds = $QueryIds | ForEach-Object { ($_ -replace '^"|"$', '').Trim() } | Where-Object { $_ }

$env:CUDA_VISIBLE_DEVICES = ""
if (-not $env:MKM_LOGOS_ANN_LITE_ST_MODEL) {
    $env:MKM_LOGOS_ANN_LITE_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
}

& py scripts/build_logos_concept_bridge_registry_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$args = @(
    "scripts/run_magic_orb_question_insight_batch_v1.py",
    "--query-ids"
) + $QueryIds + @(
    "--expand-graph",
    "--sync-public-by-query"
)
if (-not $SkipAnnLite) {
    $args += "--include-ann-lite"
    $args += "--typology-boost"
}
if ($DryRun) { $args += "--dry-run" }

Write-Host "[gold-batch] insight rebuild: $($QueryIds -join ', ')" -ForegroundColor Cyan
& py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $DryRun) {
    & py scripts/build_logos_gold_query_eval_report_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & py scripts/verify_magic_orb_graph_bloom_assets_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[OK] gold batch insight + eval ($($QueryIds -join ', '))" -ForegroundColor Green
