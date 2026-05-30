# q02 insight chain — CPU ANN + typology boost (judgment warning before collapse).

param(

    [switch]$SkipAnnLite,

    [switch]$DryRun

)



$ErrorActionPreference = "Stop"

Set-Location "C:\workspace"



$env:CUDA_VISIBLE_DEVICES = ""

if (-not $env:MKM_LOGOS_ANN_LITE_ST_MODEL) {

    $env:MKM_LOGOS_ANN_LITE_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

}



& py scripts/build_logos_concept_bridge_registry_v1.py

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



$args = @(

    "scripts/run_magic_orb_question_insight_batch_v1.py",

    "--query-ids", "q02",

    "--expand-graph",

    "--sync-public-by-query"

)

if (-not $SkipAnnLite) {

    $args += "--include-ann-lite"

    $args += "--typology-boost"

}

if ($DryRun) { $args += "--dry-run" }



Write-Host "[q02] CPU-only insight rebuild (judgment warning typology)" -ForegroundColor Cyan

& py @args

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



if (-not $DryRun) {

    & py scripts/build_logos_gold_query_eval_report_v1.py

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

}



Write-Host "[OK] q02 insight + gold eval" -ForegroundColor Green

