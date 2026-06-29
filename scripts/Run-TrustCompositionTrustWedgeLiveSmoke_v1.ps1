# Live smoke: Trust Composition trust_wedge on jema-ai hub + personadiary ops + clinician footer.
param(
    [switch]$SkipHub,
    [switch]$SkipPersonadiary,
    [switch]$SkipClinician
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failed = 0
if (-not $SkipHub) {
    node scripts/smoke-jemaai-hub-trust-wedge-live.mjs
    if ($LASTEXITCODE -ne 0) { $failed++ }
}
if (-not $SkipPersonadiary) {
    node scripts/smoke-personadiary-ops-trust-wedge-live.mjs
    if ($LASTEXITCODE -ne 0) { $failed++ }
}
if (-not $SkipClinician) {
    node scripts/smoke-jemaai-clinician-trust-footer-live.mjs
    if ($LASTEXITCODE -ne 0) { $failed++ }
}
if ($failed -gt 0) { exit 1 }
Write-Host 'OK: trust wedge live smoke passed.' -ForegroundColor Green
exit 0
