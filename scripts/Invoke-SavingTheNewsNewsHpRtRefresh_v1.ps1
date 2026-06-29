<#
.SYNOPSIS
  NEWS-HP-RT full re-bench when refresh gate allows (default not_before 2026-06-08).

.EXAMPLE
  pwsh -File scripts\Invoke-SavingTheNewsNewsHpRtRefresh_v1.ps1
  pwsh -File scripts\Invoke-SavingTheNewsNewsHpRtRefresh_v1.ps1 -Force
#>
param(
    [string]$NotBefore = "2026-06-08",
    [double]$MinHoursSinceBench = 144,
    [switch]$Force,
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$gateArgs = @(
    (Join-Path $root 'scripts\check_saving_the_news_news_hp_rt_refresh_gate_v1.py'),
    '--not-before', $NotBefore,
    '--min-hours-since-bench', "$MinHoursSinceBench",
    '--write-json'
)
if ($Force) { $gateArgs += '--force' }

& py @gateArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$gatePath = Join-Path $root 'docs\final\artifacts\saving_the_news_news_hp_rt_refresh_gate_v1_latest.json'
$gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
if (-not $gate.refresh_allowed) {
    Write-Host "SKIP: NEWS-HP-RT refresh gate HOLD ($($gate.decision_label))" -ForegroundColor Yellow
    if ($gate.blocked_reasons) {
        Write-Host "  reasons: $($gate.blocked_reasons -join '; ')"
    }
    exit 0
}

Write-Host "=== NEWS-HP-RT full refresh (gate $($gate.decision_label)) ===" -ForegroundColor Cyan
$phaseArgs = @()
if ($SkipPytest) { $phaseArgs += '-SkipPytest' }
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Run-SavingTheNewsPhase3bHyperPersonal_v1.ps1') @phaseArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== NEWS-EVO-BENCH aggregate (post HP refresh) ===" -ForegroundColor Cyan
& py (Join-Path $root 'scripts\run_saving_the_news_news_evo_bench_v1.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py (Join-Path $root 'scripts\build_saving_the_news_phase4_dual_arch_status_v1.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Invoke-SavingTheNewsNewsHpRtRefresh_v1: OK" -ForegroundColor Green
exit 0
