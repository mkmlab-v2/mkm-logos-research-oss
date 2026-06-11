# PersonaDiary preview — live design + ops smoke (apex HTML hub footer + APIs).
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-PersonadiaryPortalDesignSmoke_v1.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host '[personadiary] live ops + design hub footer smoke...' -ForegroundColor Cyan
& py scripts/run_personadiary_live_ops_smoke_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Run-PersonadiaryPortalDesignSmoke_v1: OK' -ForegroundColor Green
exit 0
