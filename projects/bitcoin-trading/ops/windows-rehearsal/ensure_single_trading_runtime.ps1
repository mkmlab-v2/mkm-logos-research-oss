# Single trading runtime on Windows:
# 1) Optional: stop direct bitcoin_trading_daemon.py copies (bypass singleton lock).
# 2) Optional: start scripts/start_24h_daemon.py if none is running (singleton lock inside Python).
#
# Live vs paper: controlled by projects/bitcoin-trading/config/trading_config.yaml
#   (enable_live_trading, testnet) and env overrides ENABLE_TRADING, TESTNET.
#
# jemaai.cloud / public dashboard: run public_event_gateway.py separately (e.g. port 8788)
# and point n8n or the site at that host — see public_event_gateway.py header.
#
# Usage:
#   .\ensure_single_trading_runtime.ps1 -StopDirectCopies
#   .\ensure_single_trading_runtime.ps1 -StopDirectCopies -StartSingletonIfMissing
#
# "12AI" (Cursor): orchestration label — runtime wiring is config + n8n + gateway, not a second bot process.

param(
    [switch]$StopDirectCopies,
    [switch]$StartSingletonIfMissing,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$startScript = Join-Path $projectRoot "scripts\start_24h_daemon.py"
$stopDirect = Join-Path $PSScriptRoot "stop_direct_bitcoin_trading_daemon_copies.ps1"

if (-not (Test-Path $startScript)) {
    throw "Missing $startScript"
}

if ($StopDirectCopies) {
    if ($WhatIf) {
        & $stopDirect -WhatIf
    } else {
        & $stopDirect
    }
}

$hasSingleton = Get-CimInstance Win32_Process -Filter "name='python.exe'" |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match 'start_24h_daemon\.py') }

if ($hasSingleton) {
    $p = @($hasSingleton)[0]
    Write-Host "[ensure-runtime] start_24h_daemon already running (PID=$($p.ProcessId))"
} elseif ($StartSingletonIfMissing) {
    if ($WhatIf) {
        Write-Host "[whatif] Would Start-Process py $startScript in $projectRoot"
    } else {
        Write-Host "[ensure-runtime] Starting singleton: py $startScript"
        Start-Process -FilePath "py" -ArgumentList "`"$startScript`"" -WorkingDirectory $projectRoot -WindowStyle Hidden
    }
} else {
    Write-Host "[ensure-runtime] No start_24h_daemon.py process found (use -StartSingletonIfMissing to launch)."
}
