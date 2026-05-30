# CPU-only typology boost for Magic Orb ANN-lite artifacts (no GPU / no Nemotron).
param(
    [string[]]$QueryIds = @("q04", "q06"),
    [switch]$IncludeQ08,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$ids = @($QueryIds)
if ($IncludeQ08) { $ids += "q08" }

$fixture = Get-Content "docs/final/fixtures/magic_orb_question_insight_queries_v1.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$queryById = @{}
foreach ($it in $fixture.items) { $queryById[$it.id] = $it.query_ko }

foreach ($qid in $ids | Select-Object -Unique) {
    $annPath = "reports/magic_orb_insight_by_query/ann_query_${qid}_latest.json"
    if (-not (Test-Path $annPath)) {
        Write-Host "[SKIP] $qid — missing $annPath" -ForegroundColor Yellow
        continue
    }
    $query = $queryById[$qid]
    if (-not $query) {
        Write-Host "[SKIP] $qid — no query text in fixture" -ForegroundColor Yellow
        continue
    }
    $args = @(
        "scripts/apply_logos_ann_typology_boost_v1.py",
        "--ann-query-json", $annPath,
        "--query-id", $qid,
        "--query", $query
    )
    if ($DryRun) { $args += "--dry-run" }
    & py @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[OK] typology boost batch done (CPU-only)" -ForegroundColor Green
