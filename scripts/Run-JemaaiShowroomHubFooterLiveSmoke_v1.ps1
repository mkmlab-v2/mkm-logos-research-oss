# Live smoke: jemaai.cloud showroom hub footer (static HTML).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-JemaaiShowroomHubFooterLiveSmoke_v1.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
node scripts/smoke-jemaai-showroom-hub-footer-live.mjs
exit $LASTEXITCODE
