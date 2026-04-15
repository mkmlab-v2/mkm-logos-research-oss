Param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$StatusJson = "docs/final/artifacts/kospi_biblical_single_lane_stability_status_latest.json",
    [double]$GraceHours = 2.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Send-WatchdogAlert {
    param(
        [string]$Event,
        [hashtable]$Details
    )
    $webhook = $env:KOSPI_BIBLICAL_STABILITY_ALARM_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        return
    }
    $payload = [ordered]@{
        event = $Event
        ts_utc = ([DateTimeOffset]::UtcNow).ToString("o")
        source = "run_kospi_biblical_single_lane_stability_watchdog.ps1"
        details = $Details
    }
    try {
        $json = $payload | ConvertTo-Json -Depth 8 -Compress
        $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $json -ContentType "application/json; charset=utf-8" -TimeoutSec 20
    }
    catch {
        Write-Host "[watchdog] alert send failed: $($_.Exception.Message)"
    }
}

Push-Location $WorkspaceRoot
try {
    $runner = "scripts/run_kospi_biblical_single_lane_stability_check.ps1"
    if (-not (Test-Path -LiteralPath $runner)) {
        throw "Runner not found: $runner"
    }

    if (-not (Test-Path -LiteralPath $StatusJson)) {
        Write-Host "[watchdog] status missing -> run now"
        powershell -NoProfile -ExecutionPolicy Bypass -File $runner -PreferRecentOnDivergence -SyncBitcoinTradingHook -SyncTwoTrackSnapshot -Sync2050Prophecy
        if ($LASTEXITCODE -ne 0) {
            Send-WatchdogAlert -Event "kospi_biblical_stability_watchdog_run_failed" -Details @{
                reason = "status_missing"
                exit_code = $LASTEXITCODE
            }
            exit $LASTEXITCODE
        }
        exit 0
    }

    $status = Get-Content -LiteralPath $StatusJson -Raw -Encoding utf8 | ConvertFrom-Json
    $now = [DateTimeOffset]::UtcNow
    $nextEligible = [DateTimeOffset]::Parse([string]$status.next_eligible_streak_ts_utc)
    $stabilityGo = [bool]$status.stability_go
    $readyStreak = [int]$status.ready_streak
    $streakRequired = [int]$status.streak_required
    $grace = [TimeSpan]::FromHours([Math]::Max(0.0, $GraceHours))

    if ($stabilityGo) {
        Write-Host "[watchdog] already stable ($readyStreak/$streakRequired) -> no action"
        exit 0
    }

    if ($now -ge $nextEligible.Add($grace)) {
        Write-Host "[watchdog] overdue past next eligible + grace -> run now"
        powershell -NoProfile -ExecutionPolicy Bypass -File $runner -PreferRecentOnDivergence -SyncBitcoinTradingHook -SyncTwoTrackSnapshot -Sync2050Prophecy
        if ($LASTEXITCODE -ne 0) {
            Send-WatchdogAlert -Event "kospi_biblical_stability_watchdog_run_failed" -Details @{
                reason = "overdue_rerun_failed"
                exit_code = $LASTEXITCODE
                next_eligible_ts_utc = $nextEligible.ToString("o")
                grace_hours = $GraceHours
            }
            exit $LASTEXITCODE
        }
        Send-WatchdogAlert -Event "kospi_biblical_stability_watchdog_overdue_rerun" -Details @{
            next_eligible_ts_utc = $nextEligible.ToString("o")
            grace_hours = $GraceHours
            action = "rerun_success"
        }
        exit 0
    }

    $remaining = ($nextEligible - $now).TotalHours
    Write-Host ("[watchdog] not due yet (remaining_hours={0:N3}) -> no action" -f $remaining)
    exit 0
}
finally {
    Pop-Location
}

