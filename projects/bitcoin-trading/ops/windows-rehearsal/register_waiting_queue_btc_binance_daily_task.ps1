param(
    [string]$TaskName = "Bitcoin-WaitingQueue-BTCBinance-Daily-Strict",
    [string]$StartTime = "09:15",
    [switch]$NoStrictCloseReturn
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\run_waiting_queue_btc_binance_daily.ps1"
$strictChecker = Join-Path $projectRoot "ops\windows-rehearsal\check_waiting_queue_strict_task_flags.ps1"
$fatalChecker = Join-Path $projectRoot "ops\windows-rehearsal\check_fatal_alert_config.ps1"

if (-not (Test-Path $runner)) {
    throw "BTC Binance daily wrapper not found: $runner"
}

$strictArg = if ($NoStrictCloseReturn) { "" } else { " -StrictCloseReturn" }
$tr = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"$strictArg"

schtasks /Delete /TN $TaskName /F | Out-Null 2>&1
schtasks /Create /TN $TaskName /SC DAILY /ST $StartTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $TaskName"
Write-Host "Start time: $StartTime"
Write-Host "Command: $tr"

if (Test-Path $strictChecker) {
    & $strictChecker -TaskNames @($TaskName)
    if ($LASTEXITCODE -ne 0) {
        throw "StrictCloseReturn flag check failed for task: $TaskName"
    }
}

if (Test-Path $fatalChecker) {
    & $fatalChecker | Out-Host
}
