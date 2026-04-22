$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-CursorTradeHistory-Latest24h-15min"

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Task not found or already removed: $taskName"
    exit 0
}

Write-Host "Removed scheduled task: $taskName"
