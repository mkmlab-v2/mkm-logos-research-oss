# Saving the News Phase 3b — hyper-personal intake + NEWS-HP-RT bench (research_only).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsPhase3bHyperPersonal_v1.ps1
# Optional: -SkipHpBench -SkipPytest

param(
    [switch]$SkipHpBench,
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Phase 3b: build hyper-personal intake ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\build_hyper_personal_news_intake_v1.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipHpBench) {
    Write-Host "=== Phase 3b: NEWS-HP-RT offline bench ===" -ForegroundColor Cyan
    & py (Join-Path $root 'scripts\run_saving_the_news_news_hp_rt_bench_v1.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py (Join-Path $root 'scripts\build_hyper_personal_news_intake_v1.py') @('--news-hp-rt-status', 'COMPLETE')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "=== Phase 3b: mkmlife §10 card export ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\export_hyper_personal_news_intake_mkmlife_card_v1.py') --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Phase 3b: mkmlife observation deck (6-9 target) ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\build_mkmlife_news_observation_deck_v1.py') --max-cards 7 --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Phase 3b: status snapshot ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\build_saving_the_news_phase3b_poc_status_v1.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Phase 3b: internal roadmap closure ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\build_saving_the_news_internal_roadmap_closure_v1.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipPytest) {
    Write-Host "=== Phase 3b: pytest smoke ===" -ForegroundColor Cyan
    & py -m pytest (Join-Path $root 'tests\test_hyper_personal_news_intake_stub_v1.py') `
        (Join-Path $root 'tests\test_build_hyper_personal_news_intake_v1.py') `
        (Join-Path $root 'tests\test_export_hyper_personal_news_intake_mkmlife_card_v1.py') -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Run-SavingTheNewsPhase3bHyperPersonal_v1: OK" -ForegroundColor Green
exit 0
