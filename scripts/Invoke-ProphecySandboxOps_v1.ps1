#Requires -Version 5.1
<#
.SYNOPSIS
  Prophecy Sandbox ops: health check + optional daily chain run.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RunChain,
    [switch]$RefreshPhase3Binance,
    [switch]$SkipMarketFetch,
    [switch]$StrictHealth
    ,
    [switch]$BackfillStreamCalendar,
    [switch]$NoBackfillStreamCalendar,
    [switch]$SyncDailyThreadLog,
    [switch]$VerifyArtifacts,
    [int]$DailyThread = 5
)

$ErrorActionPreference = "Stop"
Push-Location $WorkspaceRoot
try {
    if ($RunChain) {
        $chainArgs = @("scripts/run_prophecy_sandbox_daily_chain_v1.py", "--refresh-phase3-join")
        if ($RefreshPhase3Binance) { $chainArgs += "--refresh-phase3-binance" }
        if ($SkipMarketFetch) { $chainArgs += "--skip-market-fetch" }
        if ($BackfillStreamCalendar -or (-not $NoBackfillStreamCalendar)) {
            $chainArgs += "--backfill-stream-calendar"
        }
        if ($SyncDailyThreadLog) {
            $chainArgs += "--sync-daily-thread-log"
            $chainArgs += @("--daily-thread", "$DailyThread")
        }
        & py @chainArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if ($VerifyArtifacts -and -not $RunChain) {
        & py scripts/verify_sandbox_prophecy_artifacts_v1.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    $healthArgs = @("scripts/check_prophecy_sandbox_health_v1.py")
    if ($StrictHealth) { $healthArgs += "--strict" }
    & py @healthArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
