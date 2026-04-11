$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-MVP-ThreeBots-15min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\orchestrator\run_mvp_three_bots.ps1"

if (-not (Test-Path $runner)) {
    throw "MVP runner not found: $runner"
}

$tr = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 15 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create MVP task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"
