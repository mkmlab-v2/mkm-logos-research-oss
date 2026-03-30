$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Direct-Watchdog-5min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\ensure_daemon_running.ps1"

if (-not (Test-Path $runner)) {
    throw "Runner not found: $runner"
}

$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 5 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"
