$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-BinanceExport-ThenCursorTradeHistory-30min"

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Task not found or already removed: $taskName"
    exit 0
}

Write-Host "Removed scheduled task: $taskName"
