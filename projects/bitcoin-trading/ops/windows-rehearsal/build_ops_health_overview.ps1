param(
    [string]$JemaaiPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_alert_health_latest.json",
    [string]$BlindReplayPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\blind_replay_multi_seed_health_latest.json",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_health_overview_latest.json"
)

$ErrorActionPreference = "Stop"

function Read-JsonOrNull([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try { return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $null }
}

function Get-ScheduledTaskEnabledState([string]$TaskName) {
    schtasks /Query /TN $TaskName /V /FO LIST > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        return [ordered]@{ exists = $false; enabled = $false; status = "NOT_FOUND" }
    }
    $raw = schtasks /Query /TN $TaskName /V /FO LIST
    $statusLine = $raw | Where-Object { $_ -match "^Scheduled Task State:\s+" } | Select-Object -First 1
    if (-not $statusLine) {
        $statusLine = $raw | Where-Object { $_ -match "^Status:\s+" } | Select-Object -First 1
    }
    $status = ($statusLine -replace "^[^:]+:\s+", "").Trim()
    $enabled = $false
    if ($status -match "Enabled|Ready|Running") { $enabled = $true }
    return [ordered]@{ exists = $true; enabled = $enabled; status = $status }
}

function Test-BtcFallbackGuard([string]$scriptPath) {
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        return [ordered]@{ exists = $false; pending_close_guard = $false; strict_fallback_guard = $false; ok = $false }
    }
    $text = Get-Content -LiteralPath $scriptPath -Raw -Encoding UTF8
    $hasPendingClose = $text -match "fallback=PENDING_CLOSE"
    $hasStrictGuard = $text -match "StrictCloseReturn enabled: close return could not be resolved"
    return [ordered]@{
        exists = $true
        pending_close_guard = [bool]$hasPendingClose
        strict_fallback_guard = [bool]$hasStrictGuard
        ok = ([bool]$hasPendingClose -and [bool]$hasStrictGuard)
    }
}

$jemaai = Read-JsonOrNull -path $JemaaiPath
$blind = Read-JsonOrNull -path $BlindReplayPath
$jemaaiOk = ($null -ne $jemaai) -and [bool]$jemaai.overall_ok
$blindOk = ($null -ne $blind) -and [bool]$blind.overall_ok
$dryTask = Get-ScheduledTaskEnabledState -TaskName "Bitcoin-Fused-QuantPixel-SOP-Daily"
$liveTask = Get-ScheduledTaskEnabledState -TaskName "Bitcoin-Fused-QuantPixel-SOP-Live-Daily"
$mutexOk = ($dryTask.exists -and $liveTask.exists) -and ($dryTask.enabled -xor $liveTask.enabled)
$fallbackCheck = Test-BtcFallbackGuard -scriptPath "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_waiting_queue_btc_binance_daily.ps1"
$overall = $jemaaiOk -and $blindOk -and $mutexOk -and $fallbackCheck.ok

$obj = [ordered]@{
    schema = "ops_health_overview_v2"
    checked_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    overall_ok = $overall
    degraded = (-not $overall)
    jemaai_e2e_alert = [ordered]@{
        available = ($null -ne $jemaai)
        overall_ok = $jemaaiOk
        path = $JemaaiPath
        smoke_ok_latest = if ($null -ne $jemaai) { $jemaai.smoke_ok_latest } else { $null }
        showroom_quality_hooks_ok_latest = if ($null -ne $jemaai) { $jemaai.showroom_quality_hooks_ok_latest } else { $null }
        failure_reason_text = if ($null -ne $jemaai) { $jemaai.failure_reason_text } else { $null }
    }
    blind_replay_multi_seed = [ordered]@{
        available = ($null -ne $blind)
        overall_ok = $blindOk
        path = $BlindReplayPath
        status_recent = if ($null -ne $blind) { $blind.status_recent } else { $null }
        status_age_minutes = if ($null -ne $blind) { $blind.status_age_minutes } else { $null }
        best_balanced_accuracy_mean = if ($null -ne $blind) { $blind.metrics.balanced_accuracy_mean } else { $null }
        best_hit_rate_mean = if ($null -ne $blind) { $blind.metrics.hit_rate_mean } else { $null }
        failure_reason_text = if ($null -ne $blind) { $blind.failure_reason_text } else { $null }
    }
    fused_mode_mutex = [ordered]@{
        overall_ok = $mutexOk
        dry_task = $dryTask
        live_task = $liveTask
    }
    btc_fallback_guard = [ordered]@{
        overall_ok = $fallbackCheck.ok
        script_path = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_waiting_queue_btc_binance_daily.ps1"
        exists = $fallbackCheck.exists
        pending_close_guard = $fallbackCheck.pending_close_guard
        strict_fallback_guard = $fallbackCheck.strict_fallback_guard
    }
}

$json = $obj | ConvertTo-Json -Depth 6
$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Host $json
Write-Host ("Saved ops overview: {0}" -f $OutputPath)
if (-not $overall) { exit 1 }
exit 0
