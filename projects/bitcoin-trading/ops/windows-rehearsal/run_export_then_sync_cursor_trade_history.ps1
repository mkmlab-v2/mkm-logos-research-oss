param(
    [double]$ExportHours = 168,
    [int]$SyncWindowHours = 24,
    [switch]$RunPromotionGate
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$exportScript = Join-Path $projectRoot "scripts\export_binance_fills_to_cursor_trade_history_v1.py"

if (-not (Test-Path -LiteralPath $exportScript)) {
    throw "Export script not found: $exportScript"
}

Set-Location $projectRoot

$pyArgs = @(
    $exportScript,
    "--hours", "$ExportHours",
    "--run-sync",
    "--sync-hours", "$SyncWindowHours"
)
if ($RunPromotionGate) {
    $pyArgs += "--run-promotion-gate"
}

py @pyArgs
if ($LASTEXITCODE -ne 0) {
    throw "export_binance_fills_to_cursor_trade_history_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[OK] Binance export + cursor_trade_history sync complete"
