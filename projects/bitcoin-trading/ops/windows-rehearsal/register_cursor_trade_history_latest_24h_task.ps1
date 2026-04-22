$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-CursorTradeHistory-Latest24h-15min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "scripts\sync_cursor_trade_history_latest_24h.py"
$pythonExe = "py"
$sourceDir = "C:\workspace\projects\bitcoin-trading\exports\cursor_trade_history"
$destDir = "C:\workspace\projects\bitcoin-trading\exports\cursor_trade_history"

if (-not (Test-Path $runner)) {
    throw "Sync script not found: $runner"
}

$tr = "$pythonExe `"$runner`" --source-dir `"$sourceDir`" --dest-dir `"$destDir`" --run-promotion-gate"

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 15 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"
