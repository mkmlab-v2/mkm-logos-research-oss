Param(
    [string]$TaskName = "MKM-KOSPI-Biblical-SingleLane-Stability-Daily",
    [string]$RunTime = "03:20",
    [switch]$Remove
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_kospi_biblical_single_lane_stability_check.ps1"

if ($Remove) {
    schtasks /Delete /TN $TaskName /F | Out-Null
    Write-Host "[task] removed: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner script not found: $runner"
}

$taskCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`" -PreferRecentOnDivergence -SyncBitcoinTradingHook -SyncTwoTrackSnapshot -Sync2050Prophecy"
schtasks /Create `
    /TN $TaskName `
    /SC DAILY `
    /ST $RunTime `
    /TR $taskCommand `
    /F | Out-Null

Write-Host "[task] registered: $TaskName"
Write-Host "[task] schedule: DAILY $RunTime"
Write-Host "[task] command: $taskCommand"

