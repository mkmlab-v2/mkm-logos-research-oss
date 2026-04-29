$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-NoFill-Stall-Alert-15min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\check_no_fill_stall_alert.ps1"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$tr = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -NoFillWarnMinutes 30"

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 15 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"
