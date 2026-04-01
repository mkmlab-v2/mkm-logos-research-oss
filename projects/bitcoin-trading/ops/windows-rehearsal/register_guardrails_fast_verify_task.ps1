$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Guardrails-Fast-Verify-30min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\verify_guardrails_fast.py"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Guardrails verify script not found: $runner"
}

$tr = "py `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 30 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create task: $taskName (exit=$LASTEXITCODE)"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"

