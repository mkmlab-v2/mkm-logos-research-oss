# Stops duplicate runs launched as: python .../bitcoin_trading_daemon.py (any args).
# Does NOT stop scripts/start_24h_daemon.py — that is the singleton SSOT entrypoint.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\stop_direct_bitcoin_trading_daemon_copies.ps1
#   .\stop_direct_bitcoin_trading_daemon_copies.ps1 -WhatIf

param(
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $projectRoot "src\daemon\bitcoin_trading_daemon.py"))) {
    throw "Could not resolve bitcoin-trading project root from $PSScriptRoot"
}

$targets = Get-CimInstance Win32_Process -Filter "name='python.exe'" |
    Where-Object {
        $_.CommandLine -and
        ($_.CommandLine -match 'bitcoin_trading_daemon\.py') -and
        ($_.CommandLine -notmatch 'start_24h_daemon')
    }

if (-not $targets) {
    Write-Host "[stop-direct-daemon] No direct bitcoin_trading_daemon.py processes found."
    exit 0
}

foreach ($p in $targets) {
    $procId = [int]$p.ProcessId
    $line = $p.CommandLine
    if ($line.Length -gt 160) { $line = $line.Substring(0, 160) + "..." }
    if ($WhatIf) {
        Write-Host "[whatif] Would stop PID=$procId $line"
    } else {
        Write-Host "[stop-direct-daemon] Stopping PID=$procId"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

if (-not $WhatIf) {
    Write-Host "[stop-direct-daemon] Done."
}
