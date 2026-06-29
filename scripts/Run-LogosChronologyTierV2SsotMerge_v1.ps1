# tier_v2 SSOT merge: parallel hardset eval lanes + locked_eval compare + digest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

& $py "$root\scripts\run_logos_chronology_tier_v2_ssot_merge_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: tier_v2 SSOT merge complete"
