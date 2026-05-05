$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$statusPath = Join-Path $projectRoot "memory\v2\status\trading_daemon_status.json"
$outPath = Join-Path $projectRoot "memory\v2\ops\live_trading_blockers_latest.json"

function Read-JsonOrNull([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
    } catch {
        return $null
    }
}

$status = Read-JsonOrNull -Path $statusPath
if ($null -eq $status) {
    throw "Status file missing or invalid: $statusPath"
}

$blockers = @()
$signalSummary = $null
if ($status.mkm_singular_core -and $status.mkm_singular_core.last_signal_summary) {
    $signalSummary = $status.mkm_singular_core.last_signal_summary
}

if (-not [bool]$status.running) {
    $blockers += [ordered]@{
        code = "DAEMON_NOT_RUNNING"
        severity = "critical"
        detail = "trading_daemon_status.running=false"
        action = "Run recover_live_trading_stack.ps1 and ensure watchdog task is registered."
    }
}

if (-not [bool]$status.enable_trading) {
    $blockers += [ordered]@{
        code = "TRADING_DISABLED"
        severity = "critical"
        detail = "enable_trading=false (live execution blocked)"
        action = "Re-run recover_live_trading_stack.ps1 -EnableLiveMode and verify credentials/IP permissions."
    }
}

$exchangeError = $null
if ($status.exchange_snapshot_24h) {
    $exchangeError = [string]$status.exchange_snapshot_24h.error
}
if (-not [string]::IsNullOrWhiteSpace($exchangeError)) {
    $sev = "high"
    $act = "Check exchange API connectivity/permissions."
    if ($exchangeError -match "-2015") {
        $sev = "critical"
        $act = "Binance key/IP/permission invalid. Update API key, whitelist current IP, enable Futures permission."
    } elseif ($exchangeError -match "-2014") {
        $sev = "critical"
        $act = "API key format invalid. Regenerate keys and remove hidden characters/BOM."
    } elseif ($exchangeError -match "-2019") {
        $sev = "high"
        $act = "Insufficient margin. Lower size/leverage or add margin balance."
    }
    $blockers += [ordered]@{
        code = "EXCHANGE_ERROR"
        severity = $sev
        detail = $exchangeError
        action = $act
    }
}

if ($signalSummary) {
    if ([string]$signalSummary.singular_decision -eq "HOLD") {
        $blockers += [ordered]@{
            code = "SINGULAR_CORE_HOLD"
            severity = "medium"
            detail = ("singular_reason={0}, score={1}" -f $signalSummary.singular_reason, $signalSummary.singular_score)
            action = "Tune hold threshold/override only after exchange credential errors are cleared."
        }
    }
    if ([string]$signalSummary.singular_reason -eq "score_inside_locked_band") {
        $blockers += [ordered]@{
            code = "SCORE_LOCKED_BAND"
            severity = "medium"
            detail = ("integrated_confidence={0}" -f $signalSummary.integrated_confidence)
            action = "Collect more signal history or adjust locked band config conservatively."
        }
    }
}

$resultCode = if ($blockers.Count -eq 0) { "PASS" } else { "FAIL" }
$report = [ordered]@{
    ts_local = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    status_file = $statusPath
    daemon_running = [bool]$status.running
    trading_enabled = [bool]$status.enable_trading
    testnet = $status.testnet
    blockers = $blockers
    result = $resultCode
}

$outDir = Split-Path -Parent $outPath
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Host ("result={0}" -f $resultCode)
Write-Host ("blocker_count={0}" -f $blockers.Count)
foreach ($b in $blockers) {
    Write-Host ("- [{0}] {1} :: {2}" -f $b.severity, $b.code, $b.detail)
}
Write-Host ("saved={0}" -f $outPath)

if ($resultCode -ne "PASS") { exit 1 }
exit 0
