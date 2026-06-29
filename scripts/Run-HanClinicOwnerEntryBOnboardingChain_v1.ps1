# Entry B han clinic owner onboarding — infra gate preflight + card rebuild
param(
    [string]$ScanEnv = "",
    [switch]$SkipPytest,
    [switch]$SkipCard
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$pyArgs = @("scripts/run_han_clinic_owner_entry_b_onboarding_chain_v1.py")
if ($ScanEnv) { $pyArgs += @("--scan-env", $ScanEnv) }
if ($SkipPytest) { $pyArgs += "--skip-pytest" }
if ($SkipCard) { $pyArgs += "--skip-card" }

Write-Host "`n=== Entry B onboarding chain (infra gate + card) ===" -ForegroundColor Cyan
& py @pyArgs
exit $LASTEXITCODE
