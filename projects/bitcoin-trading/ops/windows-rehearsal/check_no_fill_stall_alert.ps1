param(
    [int]$NoFillWarnMinutes = 30
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$healthPath = Join-Path $projectRoot "memory\v2\ops\live_trading_health_latest.json"
$outPath = Join-Path $projectRoot "memory\v2\ops\live_trading_nofill_alert_latest.json"

function Read-JsonOrNull([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try { return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json) } catch { return $null }
}

function To-DateTime([string]$value) {
    if ([string]::IsNullOrWhiteSpace($value)) { return $null }
    try { return [datetime]::Parse($value) } catch { return $null }
}

$health = Read-JsonOrNull -Path $healthPath
if ($null -eq $health) {
    throw "Health snapshot missing or invalid: $healthPath"
}

$now = Get-Date
$lastTradeAgeHours = $health.last_trade_age_hours
$lastTradeAgeMinutes = $null
if ($lastTradeAgeHours -ne $null -and $lastTradeAgeHours -ne "") {
    try { $lastTradeAgeMinutes = [double]$lastTradeAgeHours * 60.0 } catch { $lastTradeAgeMinutes = $null }
}

$windowAgeMinutes = $null
if ($health.trade_history_window_age_hours -ne $null -and $health.trade_history_window_age_hours -ne "") {
    try { $windowAgeMinutes = [double]$health.trade_history_window_age_hours * 60.0 } catch { $windowAgeMinutes = $null }
}

$daemonRunning = [bool]$health.daemon_running
$tradingEnabled = [bool]$health.trading_enabled
$tradeCount24h = 0
try { $tradeCount24h = [int]$health.trade_history_count_24h } catch { $tradeCount24h = 0 }

$warn = $false
$reason = "ok"
if (-not $daemonRunning) {
    $warn = $true
    $reason = "daemon_not_running"
} elseif (-not $tradingEnabled) {
    $warn = $true
    $reason = "trading_disabled"
} elseif ($windowAgeMinutes -ne $null -and $windowAgeMinutes -gt 30) {
    $warn = $true
    $reason = "trade_window_stale"
} elseif ($tradeCount24h -eq 0 -and $windowAgeMinutes -ne $null -and $windowAgeMinutes -ge $NoFillWarnMinutes) {
    $warn = $true
    $reason = "no_fills_in_window"
} elseif ($lastTradeAgeMinutes -ne $null -and $lastTradeAgeMinutes -ge $NoFillWarnMinutes) {
    $warn = $true
    $reason = "last_trade_too_old"
}

$result = [ordered]@{
    ts_local = $now.ToString("yyyy-MM-dd HH:mm:ss")
    nofill_warn_minutes = $NoFillWarnMinutes
    daemon_running = $daemonRunning
    trading_enabled = $tradingEnabled
    trade_history_count_24h = $tradeCount24h
    trade_history_window_age_minutes = $windowAgeMinutes
    last_trade_age_minutes = $lastTradeAgeMinutes
    warn = $warn
    reason = $reason
}

$outDir = Split-Path -Parent $outPath
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Host ("warn={0} reason={1}" -f $warn, $reason)
Write-Host ("saved={0}" -f $outPath)

if ($warn) { exit 1 }
exit 0
