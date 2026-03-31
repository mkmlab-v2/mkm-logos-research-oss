# @MKM12-METADATA
# Type: Ops
# Purpose: Fast verification wrapper for waiting-queue monthly check.
# Keywords: waiting-queue, verification, skip-bundle, night-watchman

param(
    [switch]$NoSkipBundle,
    [switch]$NoSkipNightWatchmanHarness,
    [double]$OverlapDriftAlertThreshold = -0.05
)

$ErrorActionPreference = "Stop"

$workspace = "C:\workspace"
$runner = Join-Path $workspace "scripts\run_waiting_queue_monthly_check.ps1"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$args = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $runner,
    "-OverlapDriftAlertThreshold", $OverlapDriftAlertThreshold
)

# Fast verification defaults:
# - Skip bundle to reduce runtime
# - Skip Night Watchman harness when policy drift can block observability checks
if (-not $NoSkipBundle) {
    $args += "-SkipBundle"
}
if (-not $NoSkipNightWatchmanHarness) {
    $args += "-SkipNightWatchmanHarness"
}

Write-Host "[waiting-queue-verify-fast] workspace=$workspace"
Write-Host "[waiting-queue-verify-fast] skip_bundle=$(-not $NoSkipBundle)"
Write-Host "[waiting-queue-verify-fast] skip_night_watchman_harness=$(-not $NoSkipNightWatchmanHarness)"
Write-Host "[waiting-queue-verify-fast] overlap_threshold=$OverlapDriftAlertThreshold"

powershell @args
if ($LASTEXITCODE -ne 0) {
    throw "Fast waiting-queue verification failed with exit code $LASTEXITCODE"
}

Write-Host "[waiting-queue-verify-fast] completed successfully."
