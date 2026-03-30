$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-V2-Execute-Guarded-15min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\v2\tasks\run_execute_cycle_guarded.ps1"

if (-not (Test-Path $runner)) {
    throw "Guarded execute runner not found: $runner"
}

$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 15 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create guarded execute task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"
