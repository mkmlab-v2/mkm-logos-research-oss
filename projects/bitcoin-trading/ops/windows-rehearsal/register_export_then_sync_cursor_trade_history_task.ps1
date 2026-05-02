$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-BinanceExport-ThenCursorTradeHistory-30min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\run_export_then_sync_cursor_trade_history.ps1"

if (-not (Test-Path $runner)) {
    throw "Task runner script not found: $runner"
}

$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 30 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"
