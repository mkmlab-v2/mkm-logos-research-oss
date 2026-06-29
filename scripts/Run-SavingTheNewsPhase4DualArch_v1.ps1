# Saving the News Phase 4 — dual architecture §11 contract (research_only).

# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsPhase4DualArch_v1.ps1



param(

    [switch]$SkipPytest

)



$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot

Set-Location $root



Write-Host "=== Phase 4: NEWS-EVO-BENCH aggregate ===" -ForegroundColor Cyan

& py (Join-Path $root 'scripts\run_saving_the_news_news_evo_bench_v1.py')

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



Write-Host "=== Phase 4: dual-arch status snapshot ===" -ForegroundColor Cyan

& py (Join-Path $root 'scripts\build_saving_the_news_phase4_dual_arch_status_v1.py')

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



& py (Join-Path $root 'scripts\build_saving_the_news_internal_roadmap_closure_v1.py')

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



if (-not $SkipPytest) {

    Write-Host "=== Phase 4: pytest smoke ===" -ForegroundColor Cyan

    & py -m pytest `
        (Join-Path $root 'tests\test_news_evo_bench_contract_v1.py') `
        (Join-Path $root 'tests\test_run_saving_the_news_news_evo_bench_v1.py') `
        -q

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

}



Write-Host "Run-SavingTheNewsPhase4DualArch_v1: OK" -ForegroundColor Green

exit 0

