$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Public-Event-Recovery-10min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$primaryRunner = Join-Path $projectRoot "ops\windows-rehearsal\run_public_event_recovery.ps1"
$fallbackRunner = Join-Path $projectRoot "ops\windows-rehearsal\ensure_public_event_gateway.ps1"
$runner = $null

if (Test-Path -LiteralPath $primaryRunner) {
    $runner = $primaryRunner
} elseif (Test-Path -LiteralPath $fallbackRunner) {
    $runner = $fallbackRunner
} else {
    throw "Recovery runner not found (primary/fallback): $primaryRunner | $fallbackRunner"
}

$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 10 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create recovery task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"

