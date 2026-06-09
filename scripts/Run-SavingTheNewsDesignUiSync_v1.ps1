# Saving the News — design UI sync (mkmlife public JSON + jemaai topology slice).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsDesignUiSync_v1.ps1

param(
    [int]$MaxCards = 7,
    [switch]$SkipTopology,
    [switch]$SkipShowroomSmoke,
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Design UI: §10 mkmlife card export ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\export_hyper_personal_news_intake_mkmlife_card_v1.py') --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Design UI: pixel language + lens media slice ===" -ForegroundColor Cyan
$pixelSrc = Join-Path $root 'docs\final\artifacts\MKM_PIXEL_LANGUAGE_V1.json'
$pixelDest = Join-Path $root 'projects\mkm\mkm-life\public\data\MKM_PIXEL_LANGUAGE_V1.json'
Copy-Item -Force $pixelSrc $pixelDest
& py (Join-Path $root 'scripts\export_lens_media_playback_mkmlife_slice_v1.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Design UI: Morning Beans mkmlife card ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\export_mkm_morning_beans_mkmlife_card_v1.py') --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Design UI: mkmlife observation deck ($MaxCards cards) ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\build_mkmlife_news_observation_deck_v1.py') --max-cards $MaxCards --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipTopology) {
    Write-Host "=== Design UI: jemaai topology + matrix panel slice ===" -ForegroundColor Cyan
    & py (Join-Path $root 'scripts\build_saving_the_news_showroom_topology_slice_v1.py') --display-mode public_showroom
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py (Join-Path $root 'scripts\check_saving_the_news_public_copy_gate_v1.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "=== Design UI: status snapshot ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\build_saving_the_news_design_ui_status_v1.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $root 'scripts\build_saving_the_news_internal_roadmap_closure_v1.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipShowroomSmoke) {
    Write-Host "=== Design UI: showroom local smoke (staging) ===" -ForegroundColor Cyan
    $smokeArgs = @('-SkipIngest')
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Run-SavingTheNewsShowroomLocalSmoke_v1.ps1') @smokeArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipPytest) {
    Write-Host "=== Design UI: pytest smoke ===" -ForegroundColor Cyan
    & py -m pytest `
        (Join-Path $root 'tests\test_build_saving_the_news_design_ui_status_v1.py') `
        (Join-Path $root 'tests\test_export_hyper_personal_news_intake_mkmlife_card_v1.py') `
        (Join-Path $root 'tests\test_build_mkmlife_news_observation_deck_v1.py') `
        -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Run-SavingTheNewsDesignUiSync_v1: OK" -ForegroundColor Green
exit 0
