# Parallel readiness: NEWS-RT contract + Phase1 scope + observation smoke + adapters + fixture bench.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsParallelReadiness_v1.ps1
# Optional: -SkipObservationSmoke -SkipAdapters -SkipBenchSmoke -FullCohortBench

param(
    [switch]$SkipObservationSmoke,
    [switch]$SkipAdapters,
    [switch]$SkipBenchSmoke,
    [switch]$FullCohortBench
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[parallel] Saving the News readiness bundle" -ForegroundColor Cyan

$jobs = @()

if (-not $SkipObservationSmoke) {
    $jobs += @{
        Name = 'observation_smoke'
        Script = { param($r) Set-Location $r; & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $r 'scripts\Run-NewsObservationContractSmoke.ps1') }
    }
}
if (-not $SkipAdapters) {
    $jobs += @{
        Name = 'news_macro_adapters'
        Script = { param($r) Set-Location $r; & py (Join-Path $r 'scripts\build_btrack_news_macro_lens_adapters_v1.py') }
    }
}

$rt = Start-Job -Name 'news_rt_contract' -ScriptBlock {
    param($r)
    Set-Location $r
    & py (Join-Path $r 'scripts\build_saving_the_news_news_rt_bench_contract_v1.py')
} -ArgumentList $root

$p1 = Start-Job -Name 'phase1_scope' -ScriptBlock {
    param($r)
    Set-Location $r
    & py (Join-Path $r 'scripts\build_saving_the_news_phase1_poc_scope_v1.py')
} -ArgumentList $root

foreach ($j in $jobs) {
    $job = Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $root
    $null = Wait-Job $job
    $out = Receive-Job $job
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($job.State -eq 'Failed' -or ($job.ChildJobs | Where-Object { $_.JobStateInfo.Reason })) {
        Receive-Job $job -ErrorAction SilentlyContinue | Write-Host
        throw "Job $($j.Name) failed"
    }
    if ((Get-Job -Id $job.Id).State -eq 'Failed') { throw "Job $($j.Name) failed" }
    Remove-Job $job -Force
}

Wait-Job $rt, $p1 | Out-Null
Receive-Job $rt, $p1 | ForEach-Object { Write-Host $_ }
if ((Get-Job -Id $rt.Id).State -eq 'Failed' -or (Get-Job -Id $p1.Id).State -eq 'Failed') {
    Remove-Job $rt, $p1 -Force -ErrorAction SilentlyContinue
    exit 1
}
Remove-Job $rt, $p1 -Force

if (-not $SkipBenchSmoke) {
    Write-Host "[bench] NEWS-RT fixture smoke..." -ForegroundColor Cyan
    & py scripts/run_saving_the_news_news_rt_bench_smoke_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($FullCohortBench) {
    Write-Host "[cohort] NEWS-RT offline bench (>=120 rows)..." -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Run-SavingTheNewsNewsRtBench_v1.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    & py scripts/build_saving_the_news_phase1_poc_status_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[pytest] contract + scope + bench..." -ForegroundColor Cyan
& py -m pytest `
    tests/test_build_saving_the_news_news_rt_bench_contract_v1.py `
    tests/test_build_saving_the_news_phase1_poc_scope_v1.py `
    tests/test_run_saving_the_news_news_rt_bench_smoke_v1.py `
    tests/test_run_saving_the_news_news_rt_bench_v1.py `
    -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Run-SavingTheNewsParallelReadiness_v1: OK" -ForegroundColor Green
exit 0
