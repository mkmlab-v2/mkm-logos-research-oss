$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-BrainSync-Daily-0805"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\run_brain_sync_note.ps1"

if (-not (Test-Path $runner)) {
    throw "Brain sync runner not found: $runner"
}

$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC DAILY /ST 08:05 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create brain-sync task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"
