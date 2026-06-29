# Emergency local live trading stop (one-shot). Idempotent.
$ErrorActionPreference = 'Continue'
$WorkspaceRoot = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { 'C:\workspace' }

# User env (SSOT for watchdog Get-EnvAnyScope)
[Environment]::SetEnvironmentVariable('ALLOW_LIVE_TRADING_ON_LOCAL', '0', 'User')
[Environment]::SetEnvironmentVariable('LOCAL_DAEMON_HOLD_SHADOW', '1', 'User')
[Environment]::SetEnvironmentVariable('ENABLE_TRADING', 'false', 'User')

$tasks = @(
    '\MKM-Trading-Execution-Readiness-Loop-2H',
    '\MKM-Trading-Execution-Chain-Once',
    'Bitcoin-Direct-Watchdog-5min'
)
foreach ($tn in $tasks) {
    schtasks /End /TN $tn 2>$null | Out-Null
    schtasks /Change /TN $tn /DISABLE 2>$null | Out-Null
    $q = schtasks /Query /TN $tn /FO LIST 2>$null
    if ($LASTEXITCODE -eq 0) {
        $status = ($q | Select-String '^Status:').ToString().Trim()
        Write-Host "TASK $tn -> $status"
    } else {
        Write-Host "TASK $tn -> not found"
    }
}

# Kill only start_24h_daemon.py owners (not all python)
$killed = @()
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match 'start_24h_daemon\.py') } |
    ForEach-Object {
        Write-Host "KILL PID $($_.ProcessId) $($_.Name)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed += $_.ProcessId
    }
if (-not $killed.Count) { Write-Host 'No start_24h_daemon.py process found.' }

Write-Host 'USER ENV:'
Write-Host "  ALLOW_LIVE_TRADING_ON_LOCAL=$([Environment]::GetEnvironmentVariable('ALLOW_LIVE_TRADING_ON_LOCAL','User'))"
Write-Host "  LOCAL_DAEMON_HOLD_SHADOW=$([Environment]::GetEnvironmentVariable('LOCAL_DAEMON_HOLD_SHADOW','User'))"
Write-Host "  ENABLE_TRADING=$([Environment]::GetEnvironmentVariable('ENABLE_TRADING','User'))"

$envPath = Join-Path $WorkspaceRoot '.env'
if (Test-Path -LiteralPath $envPath) {
    $lines = Get-Content -LiteralPath $envPath -Encoding UTF8
    $et = ($lines | Where-Object { $_ -match '^ENABLE_TRADING=' }) -join '; '
    $al = ($lines | Where-Object { $_ -match '^ALLOW_LIVE_TRADING_ON_LOCAL=' }) -join '; '
    $hs = ($lines | Where-Object { $_ -match '^LOCAL_DAEMON_HOLD_SHADOW=' }) -join '; '
    Write-Host "ROOT .env: $et | $al | $hs"
}

exit 0
