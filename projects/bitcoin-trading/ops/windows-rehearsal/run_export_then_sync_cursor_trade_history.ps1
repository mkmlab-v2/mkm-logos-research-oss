param(
    [double]$ExportHours = 168,
    [int]$SyncWindowHours = 24,
    [switch]$RunPromotionGate
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$exportScript = Join-Path $projectRoot "scripts\export_binance_fills_to_cursor_trade_history_v1.py"
$workspaceDotenv = "C:\workspace\.env"

if (-not (Test-Path -LiteralPath $exportScript)) {
    throw "Export script not found: $exportScript"
}

function Get-DotenvValue([string]$Path, [string]$Key) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^\s*#' -or $line -match '^\s*$') {
            continue
        }
        $m = [regex]::Match($line, "^\s*{0}\s*=\s*(.*)\s*$" -f [regex]::Escape($Key))
        if (-not $m.Success) {
            continue
        }
        $v = $m.Groups[1].Value.Trim()
        if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
            return $v.Substring(1, $v.Length - 2)
        }
        return $v
    }
    return $null
}

Set-Location $projectRoot

$apiKey = Get-DotenvValue -Path $workspaceDotenv -Key "BINANCE_API_KEY"
$apiSecret = Get-DotenvValue -Path $workspaceDotenv -Key "BINANCE_API_SECRET"
if ([string]::IsNullOrWhiteSpace($apiKey) -or [string]::IsNullOrWhiteSpace($apiSecret)) {
    throw "Missing BINANCE_API_KEY/BINANCE_API_SECRET in $workspaceDotenv"
}
[Environment]::SetEnvironmentVariable("BINANCE_API_KEY", $apiKey, "Process")
[Environment]::SetEnvironmentVariable("BINANCE_API_SECRET", $apiSecret, "Process")
[Environment]::SetEnvironmentVariable("BINANCE_KEY_SOURCE_MODE", "dotenv_only", "Process")

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
