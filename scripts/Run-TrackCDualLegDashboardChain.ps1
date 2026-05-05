#Requires -Version 5.1
<#
.SYNOPSIS
  B-Track 듀얼 레그 적중률 산출 후 Track C 대시보드를 재생성합니다.

.DESCRIPTION
  체인:
    1) scripts/Run-BTrackOhlcvScoreAndEval.ps1
    2) scripts/build_mkm_trackc_ops_dashboard_v1.py
    3) scripts/build_mkm_trackc_ops_dashboard_exec_v1.py

  목적:
    듀얼 레그(KOSPI/BTC) 산출물과 Track C 대시보드 증거 체인을 한 번에 동기화합니다.
#>
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [int]$RecentTradingDays = 30,
    [string]$BtcCsv = "",
    [switch]$SkipEval,
    [switch]$SkipDualLegCompare
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$btrackRunner = Join-Path $WorkspaceRoot "scripts\Run-BTrackOhlcvScoreAndEval.ps1"
$dashboardBuilder = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_ops_dashboard_v1.py"
$dashboardExecBuilder = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_ops_dashboard_exec_v1.py"

if (-not (Test-Path -LiteralPath $btrackRunner)) {
    throw "Missing runner: $btrackRunner"
}
if (-not (Test-Path -LiteralPath $dashboardBuilder)) {
    throw "Missing dashboard builder: $dashboardBuilder"
}
if (-not (Test-Path -LiteralPath $dashboardExecBuilder)) {
    throw "Missing dashboard exec builder: $dashboardExecBuilder"
}

$runnerArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $btrackRunner,
    "-WorkspaceRoot", $WorkspaceRoot,
    "-RecentTradingDays", "$RecentTradingDays"
)
if (-not [string]::IsNullOrWhiteSpace($BtcCsv)) {
    $runnerArgs += @("-BtcCsv", $BtcCsv)
}
if ($SkipEval) {
    $runnerArgs += "-SkipEval"
}
if ($SkipDualLegCompare) {
    $runnerArgs += "-SkipDualLegCompare"
}

Write-Host "==> Run-BTrackOhlcvScoreAndEval.ps1 (chain)" -ForegroundColor Cyan
& pwsh @runnerArgs
if ($LASTEXITCODE -ne 0) {
    throw "Run-BTrackOhlcvScoreAndEval.ps1 exit $LASTEXITCODE"
}

Write-Host "==> build_mkm_trackc_ops_dashboard_v1.py" -ForegroundColor Cyan
& py $dashboardBuilder
if ($LASTEXITCODE -ne 0) {
    throw "build_mkm_trackc_ops_dashboard_v1.py exit $LASTEXITCODE"
}

Write-Host "==> build_mkm_trackc_ops_dashboard_exec_v1.py" -ForegroundColor Cyan
& py $dashboardExecBuilder
if ($LASTEXITCODE -ne 0) {
    throw "build_mkm_trackc_ops_dashboard_exec_v1.py exit $LASTEXITCODE"
}

Write-Host "[OK] Chain complete." -ForegroundColor Green
Write-Host "[OK] Score:      docs/final/artifacts/btrack_prophecy_score_latest.json" -ForegroundColor Green
if (-not $SkipEval) {
    Write-Host "[OK] Eval:       docs/final/artifacts/prophecy_hit_rate_eval_latest.json" -ForegroundColor Green
    if (-not $SkipDualLegCompare) {
        Write-Host "[OK] Compare:    docs/final/artifacts/prophecy_hit_rate_dual_leg_comparison_latest.json" -ForegroundColor Green
        Write-Host "[OK] Brief:      docs/final/artifacts/trackc_prophecy_dual_leg_brief_latest.json" -ForegroundColor Green
    }
}
Write-Host "[OK] Dashboard:  docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json" -ForegroundColor Green
Write-Host "[OK] Exec:       docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md" -ForegroundColor Green
