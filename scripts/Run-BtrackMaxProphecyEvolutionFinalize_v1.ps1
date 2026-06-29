#Requires -Version 5.1
<#
.SYNOPSIS
  B-track max prophecy evolution finalize — HD delegation one-shot (research_only, send_gate HOLD).

.DESCRIPTION
  1) News/macro adapters + yfinance CSV refresh (optional network)
  2) Full daily chain (4AI hybrid if Gemini key / MKM_MAX_PROPHECY_USE_GEMINI)
  3) Register daily scheduler task (Disabled by default)
  4) Pytest smoke
  5) athena_checkpoint one-liner

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-BtrackMaxProphecyEvolutionFinalize_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipFetchMarket,
    [switch]$SkipRegisterTask,
    [switch]$EnableDailyTask,
    [switch]$SkipCheckpoint
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$report = Join-Path $WorkspaceRoot "reports\btrack_max_prophecy_evolution_finalize_v1_latest.json"
$chain = Join-Path $WorkspaceRoot "scripts\run_btrack_max_prophecy_evolution_daily_chain_v1.py"

function Write-Step([string]$msg) {
    Write-Host "[MaxProphecyFinalize] $msg" -ForegroundColor Cyan
}

$steps = [ordered]@{}

Write-Step "1 daily chain (adapters + inject auto + eval + manifest)"
$pyArgs = @($chain, "--inject-mode", "auto")
if (-not $SkipFetchMarket) { $pyArgs += "--fetch-market" }
& py -3 @pyArgs
$chainExit = $LASTEXITCODE
$steps["daily_chain"] = @{ exit_code = $chainExit }
if ($chainExit -ne 0) { throw "daily chain exit $chainExit" }

Write-Step "2 pytest smokes"
& py -3 -m pytest tests/test_btrack_max_prophecy_evolution_v1.py tests/test_mkm_max_prophecy_4ai_forecast_v1.py -q
$pytestExit = $LASTEXITCODE
$steps["pytest"] = @{ exit_code = $pytestExit }
if ($pytestExit -ne 0) { throw "pytest exit $pytestExit" }

if (-not $SkipRegisterTask) {
    Write-Step "3 register scheduler (Disabled unless -EnableDailyTask)"
    $regArgs = @("-File", (Join-Path $WorkspaceRoot "scripts\Register-BtrackMaxProphecyEvolutionDailyTask.ps1"), "-At", "07:30")
    if ($EnableDailyTask) { $regArgs += "-EnableOnRegister" }
    & powershell -NoProfile -ExecutionPolicy Bypass @regArgs
    $steps["register_task"] = @{ exit_code = $LASTEXITCODE; enabled = [bool]$EnableDailyTask }
}

$checkpointLine = $null
if (-not $SkipCheckpoint) {
    Write-Step "4 athena_checkpoint"
    $checkpointLine = "B-track max prophecy evolution v1 finalize: 41q registry, 4AI inject, daily chain exit 0, send_gate HOLD"
    & py scripts/athena_checkpoint.py $checkpointLine
    $steps["checkpoint"] = @{ exit_code = $LASTEXITCODE }
    if ($LASTEXITCODE -ne 0) { throw "checkpoint exit $LASTEXITCODE" }
}

$doc = [ordered]@{
    schema             = "btrack_max_prophecy_evolution_finalize_v1"
    generated_at_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    send_gate          = "HOLD"
    research_mode      = "max_b_track"
    ok                 = $true
    steps              = $steps
    checkpoint_line    = $checkpointLine
    daily_chain_report = "reports/btrack_max_prophecy_evolution_daily_chain_v1_latest.json"
    inject_report      = "reports/mkm_max_prophecy_4ai_forecast_inject_v1_latest.json"
    manifest           = "docs/final/artifacts/btrack_max_prophecy_evolution_manifest_v1_latest.json"
}
$doc | ConvertTo-Json -Depth 6 | Out-File -LiteralPath $report -Encoding utf8

Write-Host "[MaxProphecyFinalize] DONE exit 0 -> $report" -ForegroundColor Green
exit 0
