# Capacitor hypo shell readiness — schema + scaffold paths (no npm install required).
param([switch]$Strict)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $root "scripts\verify_personadiary_native_shell_hypo_v1.py"))) {
    $root = Split-Path -Parent $PSScriptRoot
}

Push-Location $root
try {
    py scripts/verify_personadiary_native_shell_hypo_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    py -m pytest tests/test_personadiary_native_shell_hypo_v1_schema.py tests/test_personadiary_hygiene_prefs_hypo_v1_schema.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    exit 0
}
finally {
    Pop-Location
}
