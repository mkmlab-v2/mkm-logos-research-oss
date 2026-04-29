$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$statusPath = Join-Path $projectRoot "memory\v2\status\trading_daemon_status.json"
$tradesPath = Join-Path $projectRoot "exports\cursor_trade_history\trades_treatment_latest_24h.json"
$windowPath = Join-Path $projectRoot "exports\cursor_trade_history\all_trades_latest_24h.json"
$heartbeatPath = Join-Path $projectRoot "memory\trading_daemon_heartbeat.txt"
$outPath = Join-Path $projectRoot "memory\v2\ops\live_trading_health_latest.json"

function Read-JsonOrNull([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try { return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json) } catch { return $null }
}

function Get-AgeHours([string]$ts) {
    if ([string]::IsNullOrWhiteSpace($ts)) { return $null }
    try {
        $d = [datetime]::Parse($ts)
        return [math]::Round((((Get-Date).ToUniversalTime()) - $d.ToUniversalTime()).TotalHours, 3)
    } catch {
        return $null
    }
}

$status = Read-JsonOrNull -Path $statusPath
$trades = Read-JsonOrNull -Path $tradesPath
$window = Read-JsonOrNull -Path $windowPath

$daemonRunning = $false
$tradingEnabled = $false
$testnet = $null
$fills24h = $null
$net24h = $null
$windowAgeHours = $null
$lastTradeTs = $null
$lastTradeAgeHours = $null

if ($null -ne $status) {
    $daemonRunning = [bool]$status.running
    $tradingEnabled = [bool]$status.enable_trading
    $testnet = $status.testnet
    if ($status.exchange_snapshot_24h) {
        $fills24h = $status.exchange_snapshot_24h.fills_count
        $net24h = $status.exchange_snapshot_24h.net
    }
}

if ($null -ne $window) {
    $windowAgeHours = Get-AgeHours -ts ([string]$window.generated_at_utc)
}

$tradeCount = 0
if ($trades -is [System.Collections.IEnumerable] -and $trades -isnot [string]) {
    $arr = @($trades)
    $tradeCount = $arr.Count
    if ($tradeCount -gt 0) {
        $last = $arr[$tradeCount - 1]
        if ($last) {
            $lastTradeTs = [string]$last.timestamp
            $lastTradeAgeHours = Get-AgeHours -ts $lastTradeTs
        }
    }
}

$heartbeatAgeMinutes = $null
if (Test-Path -LiteralPath $heartbeatPath) {
    try {
        $hb = [datetime]::Parse((Get-Content -LiteralPath $heartbeatPath -Raw).Trim())
        $heartbeatAgeMinutes = [math]::Round(((Get-Date) - $hb).TotalMinutes, 3)
    } catch {
        $heartbeatAgeMinutes = $null
    }
}

$ok = $daemonRunning -and $tradingEnabled -and ($heartbeatAgeMinutes -ne $null) -and ($heartbeatAgeMinutes -lt 5)
$result = [ordered]@{
    ts_local = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    daemon_running = $daemonRunning
    trading_enabled = $tradingEnabled
    testnet = $testnet
    heartbeat_age_minutes = $heartbeatAgeMinutes
    exchange_fills_24h = $fills24h
    exchange_net_24h = $net24h
    trade_history_count_24h = $tradeCount
    trade_history_window_age_hours = $windowAgeHours
    last_trade_ts = $lastTradeTs
    last_trade_age_hours = $lastTradeAgeHours
    result = if ($ok) { "PASS" } else { "FAIL" }
}

$outDir = Split-Path -Parent $outPath
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Host ("result={0}" -f $result.result)
Write-Host ("daemon_running={0}, trading_enabled={1}, heartbeat_age_minutes={2}" -f $daemonRunning, $tradingEnabled, $heartbeatAgeMinutes)
Write-Host ("fills24h={0}, net24h={1}, trade_history_count_24h={2}" -f $fills24h, $net24h, $tradeCount)
Write-Host ("window_age_hours={0}, last_trade_age_hours={1}" -f $windowAgeHours, $lastTradeAgeHours)
Write-Host ("saved={0}" -f $outPath)

if (-not $ok) { exit 1 }
exit 0
