$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Guardrails-Fast-Verify-30min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\run_guardrails_verify_with_recovery.ps1"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Wrapper runner not found: $runner"
}

$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 30 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to (re)create task: $taskName (exit=$LASTEXITCODE)"
}

Write-Host "Reconfigured scheduled task: $taskName"
Write-Host "Command: $tr"

