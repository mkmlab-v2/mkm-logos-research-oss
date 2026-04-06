<#
.SYNOPSIS
  Bounded AIDC v2 runner (no infinite loop by default).

.DESCRIPTION
  Invokes scripts/run_aidc_bounded_loop.ps1 -MaxIterations 1 per cycle, then sleeps between cycles.
  Default: one cycle and exit (safe for Task Scheduler: weekly/daily/on-demand).

.PARAMETER MaxCycles
  How many cycles to run before exiting. Default 1.

.PARAMETER SleepSecondsBetweenCycles
  Wait time after each cycle before the next (ignored when MaxCycles is 1). Default 604800 (7 days).

.PARAMETER AidcOutputSuffix
  Passed through to run_aidc_bounded_loop.ps1 (default _v2).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_aidc_auto_runner.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_aidc_auto_runner.ps1 -MaxCycles 3 -SleepSecondsBetweenCycles 3600
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [int]$MaxCycles = 1,
  [int]$SleepSecondsBetweenCycles = 604800,
  [string]$AidcOutputSuffix = "_v2",
  [int]$Step2Iterations = 30
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ($MaxCycles -lt 1) { throw "MaxCycles must be >= 1" }
if ($SleepSecondsBetweenCycles -lt 0) { throw "SleepSecondsBetweenCycles must be >= 0" }

$bounded = Join-Path $WorkspaceRoot "scripts\run_aidc_bounded_loop.ps1"

for ($c = 1; $c -le $MaxCycles; $c++) {
  $ts = (Get-Date).ToString("s")
  Write-Host ""
  Write-Host "==== AIDC auto runner cycle $c/$MaxCycles at $ts ====" -ForegroundColor Cyan

  & powershell -NoProfile -ExecutionPolicy Bypass -File $bounded `
    -WorkspaceRoot $WorkspaceRoot `
    -MaxIterations 1 `
    -Step2Iterations $Step2Iterations `
    -AidcOutputSuffix $AidcOutputSuffix

  $code = $LASTEXITCODE
  Write-Host "Cycle $c finished with exit code $code" -ForegroundColor $(if ($code -eq 0) { "Green" } else { "Yellow" })

  if ($c -lt $MaxCycles -and $SleepSecondsBetweenCycles -gt 0) {
    Write-Host "Sleeping $SleepSecondsBetweenCycles s until next cycle..." -ForegroundColor DarkGray
    Start-Sleep -Seconds $SleepSecondsBetweenCycles
  }
}

Write-Host "[run_aidc_auto_runner] Done after $MaxCycles cycle(s)." -ForegroundColor Green
exit 0
