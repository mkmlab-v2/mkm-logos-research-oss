param(
    [string]$JemaaiPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_alert_health_latest.json",
    [string]$BlindReplayPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\blind_replay_multi_seed_health_latest.json",
    [string]$CompressionStubHealthPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\compression_stub_health_latest.json",
    [string]$ProphecyPytestStatusPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\prophecy_alignment_pytest_status_latest.json",
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
    $startTimeLine = $raw | Where-Object { $_ -match "^Start Time:\s+" } | Select-Object -First 1
    $startTime = ($startTimeLine -replace "^Start Time:\s+", "").Trim()
    return [ordered]@{ exists = $true; enabled = $enabled; status = $status; start_time = $startTime }
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

function Test-CompressionStubCodeHealthRoute([string]$scriptPath) {
    if (-not (Test-Path -LiteralPath $scriptPath)) { return $false }
    $text = Get-Content -LiteralPath $scriptPath -Raw -Encoding UTF8
    return [bool]($text -match '@app\.get\("/health"\)' -and $text -match 'return \{"status": "ok"\}')
}

function Ensure-CompressionStub([string]$ensureScriptPath) {
    if (-not (Test-Path -LiteralPath $ensureScriptPath)) { return $false }
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $ensureScriptPath | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-ExpectedTaskStartTime([object]$taskState, [string]$expectedKoreanTimeSuffix) {
    if ($null -eq $taskState -or -not [bool]$taskState.exists) { return $false }
    $actual = [string]$taskState.start_time
    if ([string]::IsNullOrWhiteSpace($actual)) { return $false }
    return $actual.EndsWith($expectedKoreanTimeSuffix)
}

$jemaai = Read-JsonOrNull -path $JemaaiPath
$blind = Read-JsonOrNull -path $BlindReplayPath
$compression = Read-JsonOrNull -path $CompressionStubHealthPath
$prophecy = Read-JsonOrNull -path $ProphecyPytestStatusPath
$jemaaiOk = ($null -ne $jemaai) -and [bool]$jemaai.overall_ok
$blindOk = ($null -ne $blind) -and [bool]$blind.overall_ok
$compressionScriptPath = "C:\workspace\scripts\compression_token_api_stub.py"
$compressionEnsureScriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\ensure_compression_stub.ps1"
$compressionRouteOk = Test-CompressionStubCodeHealthRoute -scriptPath $compressionScriptPath
$compressionEnsureOk = Ensure-CompressionStub -ensureScriptPath $compressionEnsureScriptPath
$compressionRuntimeOk = ($null -ne $compression) -and [bool]$compression.runtime_ok
$compressionRecheck = $null
if (-not $compressionRuntimeOk) {
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:8010/health" -Method Get -TimeoutSec 3
        if ($null -ne $h -and [string]$h.status -eq "ok") {
            $compressionRuntimeOk = $true
            $compressionRecheck = $h
        }
    } catch {}
}
$compressionOk = ($compressionRuntimeOk -and $compressionRouteOk)
$prophecyOk = ($null -ne $prophecy) -and [bool]$prophecy.run_ok
$dryTask = Get-ScheduledTaskEnabledState -TaskName "Bitcoin-Fused-QuantPixel-SOP-Daily"
$liveTask = Get-ScheduledTaskEnabledState -TaskName "Bitcoin-Fused-QuantPixel-SOP-Live-Daily"
$mutexOk = ($dryTask.exists -and $liveTask.exists) -and ($dryTask.enabled -xor $liveTask.enabled)
$dualStrictTask = Get-ScheduledTaskEnabledState -TaskName "Bitcoin-WaitingQueue-DualMarket-Daily-Strict"
$btcStrictTask = Get-ScheduledTaskEnabledState -TaskName "Bitcoin-WaitingQueue-BTCBinance-Daily-Strict"
$jemaaiTask = Get-ScheduledTaskEnabledState -TaskName "Jemaai-PublicEvent-E2E-Smoke"
$blindTask = Get-ScheduledTaskEnabledState -TaskName "BlindReplay-MultiSeed-Daily"
$compressionTask = Get-ScheduledTaskEnabledState -TaskName "Compression-Stub-Ensure-Daily"
$dualStrictTimeOk = Test-ExpectedTaskStartTime -taskState $dualStrictTask -expectedKoreanTimeSuffix "9:10:00"
$btcStrictTimeOk = Test-ExpectedTaskStartTime -taskState $btcStrictTask -expectedKoreanTimeSuffix "9:15:00"
$jemaaiTimeOk = Test-ExpectedTaskStartTime -taskState $jemaaiTask -expectedKoreanTimeSuffix "9:35:00"
$blindTimeOk = Test-ExpectedTaskStartTime -taskState $blindTask -expectedKoreanTimeSuffix "10:05:00"
$compressionTimeOk = Test-ExpectedTaskStartTime -taskState $compressionTask -expectedKoreanTimeSuffix "9:00:00"
$strictScheduleOk = ($dualStrictTask.exists -and $dualStrictTask.enabled -and $dualStrictTimeOk) -and ($btcStrictTask.exists -and $btcStrictTask.enabled -and $btcStrictTimeOk)
$opsScheduleOk = $strictScheduleOk -and ($jemaaiTask.exists -and $jemaaiTask.enabled -and $jemaaiTimeOk) -and ($blindTask.exists -and $blindTask.enabled -and $blindTimeOk) -and ($compressionTask.exists -and $compressionTask.enabled -and $compressionTimeOk)
$fallbackCheck = Test-BtcFallbackGuard -scriptPath "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_waiting_queue_btc_binance_daily.ps1"
$overall = $jemaaiOk -and $blindOk -and $mutexOk -and $opsScheduleOk -and $fallbackCheck.ok -and $compressionOk -and $prophecyOk

$obj = [ordered]@{
    schema = "ops_health_overview_v3"
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
    strict_task_schedule = [ordered]@{
        overall_ok = $strictScheduleOk
        dual_market = [ordered]@{
            expected_start = "09:10"
            start_time_ok = $dualStrictTimeOk
            task = $dualStrictTask
        }
        btc_binance = [ordered]@{
            expected_start = "09:15"
            start_time_ok = $btcStrictTimeOk
            task = $btcStrictTask
        }
    }
    ops_task_schedule = [ordered]@{
        overall_ok = $opsScheduleOk
        jemaai_e2e = [ordered]@{
            expected_start = "09:35"
            start_time_ok = $jemaaiTimeOk
            task = $jemaaiTask
        }
        blind_replay = [ordered]@{
            expected_start = "10:05"
            start_time_ok = $blindTimeOk
            task = $blindTask
        }
        compression_stub = [ordered]@{
            expected_start = "09:00"
            start_time_ok = $compressionTimeOk
            task = $compressionTask
        }
    }
    btc_fallback_guard = [ordered]@{
        overall_ok = $fallbackCheck.ok
        script_path = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_waiting_queue_btc_binance_daily.ps1"
        exists = $fallbackCheck.exists
        pending_close_guard = $fallbackCheck.pending_close_guard
        strict_fallback_guard = $fallbackCheck.strict_fallback_guard
    }
    compression_stub_health = [ordered]@{
        available = ($null -ne $compression)
        overall_ok = $compressionOk
        path = $CompressionStubHealthPath
        endpoint = if ($null -ne $compression) { $compression.endpoint } else { "http://127.0.0.1:8010/health" }
        runtime_ok = $compressionRuntimeOk
        code_health_route_ok = $compressionRouteOk
        ensure_script = $compressionEnsureScriptPath
        ensure_ok = $compressionEnsureOk
        runtime_recheck_after_ensure = ($null -ne $compressionRecheck)
    }
    prophecy_alignment_pytest = [ordered]@{
        available = ($null -ne $prophecy)
        overall_ok = $prophecyOk
        path = $ProphecyPytestStatusPath
        run_ok = if ($null -ne $prophecy) { $prophecy.run_ok } else { $null }
        exit_code = if ($null -ne $prophecy) { $prophecy.exit_code } else { $null }
        elapsed_sec = if ($null -ne $prophecy) { $prophecy.elapsed_sec } else { $null }
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
