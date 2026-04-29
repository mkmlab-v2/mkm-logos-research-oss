param(
    [int]$WaitSeconds = 30,
    [switch]$EnableLiveMode
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$ensureScript = Join-Path $projectRoot "ops\windows-rehearsal\ensure_daemon_running.ps1"
$registerTaskScript = Join-Path $projectRoot "ops\windows-rehearsal\register_direct_watchdog_task.ps1"
$heartbeatPath = Join-Path $projectRoot "memory\trading_daemon_heartbeat.txt"
$statusPath = Join-Path $projectRoot "memory\v2\status\trading_daemon_status.json"
$tradeWindowPath = Join-Path $projectRoot "exports\cursor_trade_history\all_trades_latest_24h.json"
$logPath = Join-Path $projectRoot "memory\watchdog_direct.log"

function Write-Step([string]$msg) {
    Write-Host "[recover] $msg"
}

function Set-EnvUser([string]$Name, [string]$Value) {
    [Environment]::SetEnvironmentVariable($Name, $Value, "User")
    [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
}

function Force-StartLiveDaemon {
    $daemonArg = "scripts/start_24h_daemon.py"
    [Environment]::SetEnvironmentVariable("TESTNET", "false", "Process")
    [Environment]::SetEnvironmentVariable("ENABLE_TRADING", "true", "Process")
    Start-Process -FilePath "py.exe" -ArgumentList @($daemonArg) -WorkingDirectory $projectRoot -WindowStyle Hidden
}

function Get-JsonOrNull([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
    } catch {
        return $null
    }
}

if (-not (Test-Path -LiteralPath $projectRoot)) {
    throw "Project root not found: $projectRoot"
}
if (-not (Test-Path -LiteralPath $ensureScript)) {
    throw "Required script missing: $ensureScript"
}
if (-not (Test-Path -LiteralPath $registerTaskScript)) {
    throw "Required script missing: $registerTaskScript"
}

Set-Location $projectRoot

Write-Step "Reset STOP kill-switch if present"
$stopPath = Join-Path $projectRoot "memory\STOP.txt"
if (Test-Path -LiteralPath $stopPath) {
    Remove-Item -LiteralPath $stopPath -Force
}

if ($EnableLiveMode) {
    Write-Step "Enable local live mode (mainnet + trading on)"
    Set-EnvUser -Name "ALLOW_LIVE_TRADING_ON_LOCAL" -Value "1"
    Set-EnvUser -Name "LOCAL_DAEMON_PAPER_STRICT" -Value "0"
    Set-EnvUser -Name "LOCAL_DAEMON_HOLD_SHADOW" -Value "0"
    Set-EnvUser -Name "TESTNET" -Value "false"
    Set-EnvUser -Name "ENABLE_TRADING" -Value "true"
} else {
    Write-Step "Live mode unchanged (pass -EnableLiveMode to force)"
}

Write-Step "Register direct watchdog scheduled task"
powershell -NoProfile -ExecutionPolicy Bypass -File $registerTaskScript | Out-Null

Write-Step "Run watchdog once now"
powershell -NoProfile -ExecutionPolicy Bypass -File $ensureScript | Out-Null

Write-Step "Wait $WaitSeconds seconds for daemon heartbeat/status update"
Start-Sleep -Seconds $WaitSeconds

$heartbeatFresh = $false
$heartbeatAgeMinutes = $null
if (Test-Path -LiteralPath $heartbeatPath) {
    try {
        $hb = [datetime]::Parse((Get-Content -LiteralPath $heartbeatPath -Raw).Trim())
        $heartbeatAgeMinutes = ((Get-Date) - $hb).TotalMinutes
        $heartbeatFresh = $heartbeatAgeMinutes -lt 5
    } catch {
        $heartbeatFresh = $false
    }
}

$statusObj = Get-JsonOrNull -Path $statusPath
$statusRunning = $null
$statusTradingEnabled = $null
$statusTestnet = $null
$statusExchangeError = $null
if ($null -ne $statusObj) {
    $statusRunning = $statusObj.running
    $statusTradingEnabled = $statusObj.enable_trading
    $statusTestnet = $statusObj.testnet
    if ($statusObj.exchange_snapshot_24h) {
        $statusExchangeError = $statusObj.exchange_snapshot_24h.error
    }
}

# Live-mode self-heal:
# If daemon is up but still in non-trading mode without -2015,
# force one recycle so a fresh process picks ENABLE_TRADING=true.
if (
    $EnableLiveMode -and
    ($statusRunning -eq $true) -and
    (($statusTradingEnabled -ne $true) -or ($statusTestnet -eq $true)) -and
    ([string]::IsNullOrWhiteSpace([string]$statusExchangeError) -or -not ([string]$statusExchangeError -match "-2015"))
) {
    Write-Step "Live mode requested but daemon not in live profile without -2015. Forcing single recycle."
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -and $_.CommandLine -match "start_24h_daemon\.py" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
    Force-StartLiveDaemon
    Start-Sleep -Seconds 8
    $statusObj = Get-JsonOrNull -Path $statusPath
    if ($null -ne $statusObj) {
        $statusRunning = $statusObj.running
        $statusTradingEnabled = $statusObj.enable_trading
        $statusTestnet = $statusObj.testnet
        $statusExchangeError = $null
        if ($statusObj.exchange_snapshot_24h) {
            $statusExchangeError = $statusObj.exchange_snapshot_24h.error
        }
    }
}

$tradeObj = Get-JsonOrNull -Path $tradeWindowPath
$tradeAgeHours = $null
if ($null -ne $tradeObj -and $tradeObj.generated_at_utc) {
    try {
        $g = [datetime]::Parse([string]$tradeObj.generated_at_utc)
        $tradeAgeHours = ((Get-Date).ToUniversalTime() - $g.ToUniversalTime()).TotalHours
    } catch {
        $tradeAgeHours = $null
    }
}

$daemonProcCount = @(
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -and $_.CommandLine -match "start_24h_daemon\.py" }
).Count

$result = [ordered]@{
    ts_local = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    project_root = $projectRoot
    daemon_process_count = $daemonProcCount
    heartbeat_file_exists = (Test-Path -LiteralPath $heartbeatPath)
    heartbeat_age_minutes = $heartbeatAgeMinutes
    heartbeat_fresh_under_5m = $heartbeatFresh
    status_file_exists = (Test-Path -LiteralPath $statusPath)
    status_running = $statusRunning
    status_enable_trading = $statusTradingEnabled
    status_testnet = $statusTestnet
    status_exchange_error = $statusExchangeError
    trade_24h_file_exists = (Test-Path -LiteralPath $tradeWindowPath)
    trade_24h_generated_age_hours = $tradeAgeHours
    watchdog_log_exists = (Test-Path -LiteralPath $logPath)
}

$ok = ($daemonProcCount -gt 0) -and $heartbeatFresh -and ($statusRunning -eq $true)
if ($EnableLiveMode) {
    $ok = $ok -and ($statusTradingEnabled -eq $true) -and ($statusTestnet -eq $false)
}
if (-not [string]::IsNullOrWhiteSpace([string]$statusExchangeError) -and ([string]$statusExchangeError -match "-2015")) {
    $ok = $false
}
$result["result"] = if ($ok) { "PASS" } else { "FAIL" }

$outPath = Join-Path $projectRoot "memory\v2\ops\live_stack_recovery_report_latest.json"
$outDir = Split-Path -Parent $outPath
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Step ("result={0}" -f $result.result)
Write-Step ("daemon_process_count={0}, heartbeat_fresh={1}, status_running={2}" -f $daemonProcCount, $heartbeatFresh, $statusRunning)
Write-Step ("saved report: {0}" -f $outPath)

if (-not $ok) {
    Write-Step "tail watchdog log (last 40 lines)"
    if (Test-Path -LiteralPath $logPath) {
        Get-Content -LiteralPath $logPath -Tail 40
    } else {
        Write-Step "watchdog log missing: $logPath"
    }
    exit 1
}

exit 0
