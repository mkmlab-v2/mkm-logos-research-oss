# mkmlife portal commercialization gate — offline + build + optional live/playwright.
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-MkmlifePortalCommercializationGate_v1.ps1
#   ... -IncludeLiveSmoke
#   ... -IncludePlaywright -StrictPlaywright

param(
    [switch]$SkipBuild,
    [switch]$SkipPytest,
    [switch]$IncludeLiveSmoke,
    [switch]$IncludePlaywright,
    [switch]$StrictPlaywright,
    [string]$SmokeOrigin = 'https://mkmlife.com',
    [string]$OutJson = 'reports/mkmlife_portal_commercialization_gate_v1_latest.json'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$mkmLife = Join-Path $root 'projects/mkm/mkm-life'

Write-Host '[1/6] offline commercialization gate (deck JSON + copy SSOT)...' -ForegroundColor Cyan
& py scripts/check_mkmlife_portal_commercialization_gate_v1.py --out-json $OutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '[2/6] pixel sprite URL hard gate (MKM_PIXEL_LANGUAGE disk SSOT)...' -ForegroundColor Cyan
& py scripts/check_mkmlife_pixel_sprite_urls_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipPytest) {
    Write-Host '[3/6] pytest (portal gate + deck + skim + pixel sprite gate)...' -ForegroundColor Cyan
    & py -m pytest `
        tests/test_check_mkmlife_portal_commercialization_gate_v1.py `
        tests/test_check_mkmlife_pixel_sprite_urls_v1.py `
        tests/test_build_mkmlife_news_observation_deck_v1.py `
        tests/test_mkmlife_skim_read_preference_v1.py `
        tests/test_mkm_consumer_facade_v1.py `
        -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host '[3/6] skip pytest (-SkipPytest)' -ForegroundColor Yellow
}

if (-not $SkipBuild) {
    Write-Host '[4/6] mkmlife next build...' -ForegroundColor Cyan
    Push-Location $mkmLife
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
} else {
    Write-Host '[4/6] skip build (-SkipBuild)' -ForegroundColor Yellow
}

if ($IncludeLiveSmoke) {
    Write-Host "[5/6] live pixel sprite URL gate ($SmokeOrigin)..." -ForegroundColor Cyan
    & py scripts/check_mkmlife_pixel_sprite_urls_v1.py --fetch-from-origin $SmokeOrigin
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[5/6] live portal commercialization smoke ($SmokeOrigin)..." -ForegroundColor Cyan
    Push-Location $mkmLife
    try {
        $env:MKM_SMOKE_ORIGIN = $SmokeOrigin
        node scripts/smoke-mkmlife-portal-commercialization-live.mjs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        node scripts/smoke-mkmlife-askone-oracle-live-bundle.mjs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
} else {
    Write-Host '[5/6] skip live smoke (use -IncludeLiveSmoke)' -ForegroundColor DarkYellow
}

if ($IncludePlaywright) {
    Write-Host '[6/6] playwright skim/localStorage E2E...' -ForegroundColor Cyan
    Push-Location $mkmLife
    try {
        if ($StrictPlaywright) { $env:MKM_SMOKE_STRICT_PLAYWRIGHT = '1' }
        $env:MKMLIFE_BASE_URL = $SmokeOrigin
        node scripts/smoke-mkmlife-portal-skim-playwright.mjs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
} else {
    Write-Host '[6/6] skip playwright (use -IncludePlaywright)' -ForegroundColor DarkYellow
}

Write-Host 'Run-MkmlifePortalCommercializationGate_v1: OK' -ForegroundColor Green
exit 0
