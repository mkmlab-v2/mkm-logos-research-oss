# NEWS-RT offline cohort bench + Phase1 status refresh.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsNewsRtBench_v1.ps1

param(
    [string]$CohortJsonl = "docs/final/artifacts/news_observation_v1_latest.jsonl",
    [int]$MinRows = 120
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[1/3] validate cohort..." -ForegroundColor Cyan
& py scripts/validate_news_observation_jsonl_v1.py --news-jsonl $CohortJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] NEWS-RT offline cohort bench..." -ForegroundColor Cyan
& py scripts/run_saving_the_news_news_rt_bench_v1.py --cohort-jsonl $CohortJsonl --min-rows $MinRows
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] Phase1 PoC status..." -ForegroundColor Cyan
& py scripts/build_saving_the_news_phase1_poc_status_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Run-SavingTheNewsNewsRtBench_v1: OK" -ForegroundColor Green
exit 0
