$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-V2-Shadow-15min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\v2\tasks\run_shadow_cycle.ps1"

if (-not (Test-Path $runner)) {
    throw "Shadow runner not found: $runner"
}

$tr = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 15 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create shadow task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"
