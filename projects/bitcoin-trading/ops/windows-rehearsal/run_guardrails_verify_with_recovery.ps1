$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$verifyScript = Join-Path $projectRoot "ops\windows-rehearsal\verify_guardrails_fast.py"
$recoveryScript = Join-Path $projectRoot "ops\windows-rehearsal\run_public_event_recovery.ps1"
$fallbackRecoveryScript = Join-Path $projectRoot "ops\windows-rehearsal\ensure_public_event_gateway.ps1"

if (-not (Test-Path -LiteralPath $verifyScript)) {
    throw "Guardrails verify script not found: $verifyScript"
}
Write-Host "[guardrails] start fast verify"
& py $verifyScript
$verifyExit = $LASTEXITCODE

if ($verifyExit -eq 0) {
    Write-Host "[guardrails] PASS - no recovery needed"
    exit 0
}

Write-Warning "[guardrails] FAIL (exit=$verifyExit) - running recovery"
$recoveryTarget = $null
if (Test-Path -LiteralPath $recoveryScript) {
    $recoveryTarget = $recoveryScript
} elseif (Test-Path -LiteralPath $fallbackRecoveryScript) {
    $recoveryTarget = $fallbackRecoveryScript
} else {
    Write-Error "[guardrails] recovery script not found (primary/fallback)"
    exit 1
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $recoveryTarget
$recoveryExit = $LASTEXITCODE

if ($recoveryExit -ne 0) {
    Write-Error "[guardrails] recovery failed (exit=$recoveryExit)"
    exit $recoveryExit
}

Write-Host "[guardrails] recovery completed after verify failure"
exit 0

