# Post-sign-off: tier_v2 SSOT merge + readiness + human margin report + historical AB
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

& $py "$root\scripts\run_logos_chronology_hardset_closure_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: hardset closure complete"
