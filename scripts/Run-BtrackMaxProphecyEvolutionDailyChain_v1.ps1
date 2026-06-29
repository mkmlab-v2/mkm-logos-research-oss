#Requires -Version 5.1
<#
.SYNOPSIS
  Run B-track max prophecy evolution daily chain (research_only, send_gate HOLD).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-BtrackMaxProphecyEvolutionDailyChain_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [ValidateSet("research", "ops")]
    [string]$HoldoutGateProfile = "research",
    [ValidateSet("auto", "deterministic", "hybrid", "gemini")]
    [string]$InjectMode = "auto",
    [switch]$FetchMarket,
    [switch]$SkipMicroSignal,
    [switch]$SkipOhlcv,
    [switch]$SkipEvolution,
    [switch]$SkipWatchdog,
    [switch]$SkipInject
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$chain = Join-Path $WorkspaceRoot "scripts\run_btrack_max_prophecy_evolution_daily_chain_v1.py"
if (-not (Test-Path -LiteralPath $chain)) { throw "Missing: $chain" }

$pyArgs = @(
    $chain,
    "--holdout-profile", $HoldoutGateProfile,
    "--inject-mode", $InjectMode
)
if ($FetchMarket) { $pyArgs += "--fetch-market" }
if ($SkipMicroSignal) { $pyArgs += "--skip-micro-signal" }
if ($SkipOhlcv) { $pyArgs += "--skip-ohlcv" }
if ($SkipEvolution) { $pyArgs += "--skip-evolution" }
if ($SkipWatchdog) { $pyArgs += "--skip-watchdog" }
if ($SkipInject) { $pyArgs += "--skip-inject" }

& py -3 @pyArgs
exit $LASTEXITCODE
