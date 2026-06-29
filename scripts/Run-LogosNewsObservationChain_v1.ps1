# B-track: Korea/Exa news -> news_observation_v1 -> Logos theme overlay [NON_GATING].
param(
    [string]$DateFrom = "2026-06-01",
    [string]$DateTo = "2026-06-30",
    [switch]$SkipNewsFetch
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not $SkipNewsFetch) {
    py scripts/build_korea_disaster_news_context_v1.py --date-from $DateFrom --date-to $DateTo --use-exa
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    py scripts/build_korea_health_infectious_news_context_v1.py --date-from $DateFrom --date-to $DateTo --use-exa --exa-per-query 25
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

py scripts/ingest_korea_context_to_news_observation_v1.py --validate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/ingest_korea_context_to_news_observation_v1.py `
    --articles-json reports/korea_health_infectious_news_articles_v1.json `
    --source-id-prefix korea_health `
    --dataset-partition train_holdout `
    --validate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_logos_news_theme_overlay_v1.py --date-from $DateFrom --date-to $DateTo
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_logos_insight_bundle_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/assemble_three_lens_sphere_envelope_v1.py
exit $LASTEXITCODE
