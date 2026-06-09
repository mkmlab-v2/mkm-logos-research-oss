# mkmlife Observation Deck fusion chain (B-track, research_only).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-MkmlifeNewsObservationFusionChain_v1.ps1

param(
    [string]$NewsJsonl = "docs/final/artifacts/news_observation_v1_latest.jsonl",
    [int]$MaxCards = 5,
    [switch]$SkipBench,
    [switch]$FetchRss,
    [switch]$SkipRss,
    [switch]$DeployMkmlifeAssets,
    [switch]$FullMkmlifeDeploy
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($FetchRss -and -not $SkipRss) {
    Write-Host "[0/6] fetch RSS -> external_feed_drop..." -ForegroundColor Cyan
    & py scripts/fetch_rss_to_external_feed_drop_v1.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: RSS fetch returned no items; continuing with existing drop if any." -ForegroundColor Yellow
    }
    Write-Host "[0b/6] validate external_feed_drop..." -ForegroundColor Cyan
    & py scripts/load_external_feed_drop_with_fallback_v1.py --allow-empty
    if ($LASTEXITCODE -ne 0) { Write-Host "WARN: external feed validation degraded." -ForegroundColor Yellow }
    Write-Host "[0c/6] ingest external_feed -> news_observation..." -ForegroundColor Cyan
    & py scripts/build_news_observation_from_external_feed_v1.py `
        --external-feed-json docs/final/artifacts/external_feed_drop_latest.validated.json `
        --append-existing-jsonl $NewsJsonl `
        --output-jsonl $NewsJsonl `
        --validate
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[1/6] validate news_observation cohort..." -ForegroundColor Cyan
& py scripts/validate_news_observation_jsonl_v1.py --news-jsonl $NewsJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipBench) {
    Write-Host "[2/6] NEWS-RT offline bench (quality gate inputs)..." -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsNewsRtBench_v1.ps1 -CohortJsonl $NewsJsonl
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[2/6] skip bench (-SkipBench)" -ForegroundColor Yellow
}

Write-Host "[3/6] build mkmlife Observation Deck..." -ForegroundColor Cyan
& py scripts/build_mkmlife_news_observation_deck_v1.py --news-jsonl $NewsJsonl --max-cards $MaxCards --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/6] deck pytest smoke..." -ForegroundColor Cyan
& py -m pytest tests/test_build_mkmlife_news_observation_deck_v1.py tests/test_fetch_rss_to_external_feed_drop_v1.py tests/test_mkmlife_rss_minimal.py tests/test_check_mkmlife_portal_commercialization_gate_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($DeployMkmlifeAssets -or $FullMkmlifeDeploy) {
    $deployArgs = @("-SkipProbe", "-SkipKvSync")
    if ($FullMkmlifeDeploy) {
        Write-Host "[5/6] mkmlife full deploy (build + worker)..." -ForegroundColor Cyan
        $deployArgs += "-FullDeploy"
    } else {
        Write-Host "[5/6] mkmlife asset deploy (wrangler; /news-deck route needs -FullMkmlifeDeploy once)..." -ForegroundColor Cyan
        $deployArgs += "-DeployAssets"
    }
    $deployArgs += "-SkipPostDeploySmoke"
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-Op30Phase2Daily_v1.ps1 @deployArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[5/6] skip mkmlife deploy (use -DeployMkmlifeAssets)" -ForegroundColor DarkYellow
}

Write-Host "[6/6] Run-MkmlifeNewsObservationFusionChain_v1: OK" -ForegroundColor Green
exit 0
