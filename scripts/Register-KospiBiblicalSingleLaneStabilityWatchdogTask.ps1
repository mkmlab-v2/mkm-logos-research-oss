Param(
    [string]$TaskName = "MKM-KOSPI-Biblical-SingleLane-Stability-Watchdog-Hourly",
    [switch]$Remove
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_kospi_biblical_single_lane_stability_watchdog.ps1"

if ($Remove) {
    schtasks /Delete /TN $TaskName /F | Out-Null
    Write-Host "[task] removed: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Watchdog script not found: $runner"
}

$taskCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""
schtasks /Create `
    /TN $TaskName `
    /SC HOURLY `
    /MO 1 `
    /TR $taskCommand `
    /F | Out-Null

Write-Host "[task] registered: $TaskName"
Write-Host "[task] schedule: HOURLY (every 1 hour)"
Write-Host "[task] command: $taskCommand"
