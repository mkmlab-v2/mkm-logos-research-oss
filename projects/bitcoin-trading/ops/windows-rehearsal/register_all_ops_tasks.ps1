param(
    [switch]$NoStrictCloseReturn,
    [switch]$HealthcheckDryRun,
    [string]$DualMarketStartTime = "09:10",
    [string]$BtcBinanceStartTime = "09:15",
    [string]$HealthcheckStartTime = "09:05",
    [ValidateSet("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")]
    [string]$HealthcheckWeeklyDay = "MON"
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$opsDir = Join-Path $projectRoot "ops\windows-rehearsal"

$registerDual = Join-Path $opsDir "register_waiting_queue_dual_market_daily_task.ps1"
$registerBtc = Join-Path $opsDir "register_waiting_queue_btc_binance_daily_task.ps1"
$registerHealth = Join-Path $opsDir "register_fatal_alert_healthcheck_task.ps1"

foreach ($script in @($registerDual, $registerBtc, $registerHealth)) {
    if (-not (Test-Path -LiteralPath $script)) {
        throw "Required register script missing: $script"
    }
}

$dualArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $registerDual, "-StartTime", $DualMarketStartTime)
if ($NoStrictCloseReturn) {
    $dualArgs += "-NoStrictCloseReturn"
}
& powershell @dualArgs
if ($LASTEXITCODE -ne 0) {
    throw "Dual market task registration failed"
}

$btcArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $registerBtc, "-StartTime", $BtcBinanceStartTime)
if ($NoStrictCloseReturn) {
    $btcArgs += "-NoStrictCloseReturn"
}
& powershell @btcArgs
if ($LASTEXITCODE -ne 0) {
    throw "BTC Binance task registration failed"
}

$healthArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $registerHealth,
    "-StartTime", $HealthcheckStartTime,
    "-Schedule", "WEEKLY",
    "-WeeklyDay", $HealthcheckWeeklyDay
)
if (-not $HealthcheckDryRun) {
    $healthArgs += "-Send"
}
& powershell @healthArgs
if ($LASTEXITCODE -ne 0) {
    throw "Fatal alert healthcheck task registration failed"
}

$recoveryCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File `"C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\register_all_ops_tasks.ps1`""
$stamp = ([DateTimeOffset]::UtcNow).ToString("o")
$artifactPath = "C:\workspace\docs\final\artifacts\ops_task_recovery_command_latest.txt"
$artifact = @(
    "[$stamp] Standard recovery command",
    $recoveryCommand,
    ""
)
Set-Content -LiteralPath $artifactPath -Value ($artifact -join [Environment]::NewLine) -Encoding utf8

Write-Host "Recovery command:"
Write-Host $recoveryCommand
Write-Host "Recovery command artifact: $artifactPath"
Write-Host "OK all ops tasks registered"
exit 0
