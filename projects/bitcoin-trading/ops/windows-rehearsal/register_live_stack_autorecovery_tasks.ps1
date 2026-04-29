$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$recoverScript = Join-Path $projectRoot "ops\windows-rehearsal\recover_live_trading_stack.ps1"

$taskAtStartup = "Bitcoin-LiveStack-Recover-AtStartup"
$taskEvery5m = "Bitcoin-LiveStack-Recover-5min"
$taskExistingWatchdog = "Bitcoin-Direct-Watchdog-5min"

if (-not (Test-Path -LiteralPath $recoverScript)) {
    throw "Recover script not found: $recoverScript"
}

$tr = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$recoverScript`" -EnableLiveMode -WaitSeconds 20"

Write-Host "[register] command: $tr"

# Idempotent recreate (ignore if missing)
schtasks /Delete /TN $taskAtStartup /F | Out-Null 2>&1
schtasks /Delete /TN $taskEvery5m /F | Out-Null 2>&1

# At system startup (fallback to ONLOGON without admin rights)
schtasks /Create /TN $taskAtStartup /SC ONSTART /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[register] ONSTART create failed (ExitCode=$LASTEXITCODE), fallback to ONLOGON"
    schtasks /Create /TN $taskAtStartup /SC ONLOGON /TR $tr /F | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[register] startup/logon task creation skipped (permission denied or policy)."
    }
}

# Every 5 minutes
schtasks /Create /TN $taskEvery5m /SC MINUTE /MO 5 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[register] 5-minute recovery task creation failed (ExitCode=$LASTEXITCODE)"
    schtasks /Query /TN $taskExistingWatchdog | Out-Null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[register] existing watchdog task detected: $taskExistingWatchdog (reused)"
    } else {
        throw "Failed to create 5-minute task and no existing watchdog task found."
    }
}

Write-Host "[register] created tasks:"
Write-Host "  - $taskAtStartup"
Write-Host "  - $taskEvery5m"
Write-Host "  - (fallback) $taskExistingWatchdog"
Write-Host "[register] done"
