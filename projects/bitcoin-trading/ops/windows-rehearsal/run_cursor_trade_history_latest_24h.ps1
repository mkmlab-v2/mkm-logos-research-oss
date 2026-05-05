$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$scriptPath = Join-Path $projectRoot "scripts\sync_cursor_trade_history_latest_24h.py"
$sourceDir = Join-Path $projectRoot "exports\cursor_trade_history"
$destDir = $sourceDir

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Sync script not found: $scriptPath"
}

Set-Location $projectRoot
py $scriptPath --source-dir $sourceDir --dest-dir $destDir
if ($LASTEXITCODE -ne 0) {
    throw "sync_cursor_trade_history_latest_24h.py failed with exit code $LASTEXITCODE"
}

Write-Host "[cursor-trade-history] latest 24h sync done"
