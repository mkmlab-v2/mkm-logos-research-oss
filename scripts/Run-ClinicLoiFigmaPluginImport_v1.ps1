# One-shot Figma plugin import for clinic LOI variables (Starter plan).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pluginDir = Join-Path $root "projects/design/clinic_loi_figma_plugin"
$figmaUrl = "https://www.figma.com/design/8Ey3MEkXhH8EliARQ9OydE/mkm-20260624"

if (-not (Test-Path -LiteralPath (Join-Path $pluginDir "manifest.json"))) {
    Write-Error "Plugin not found: $pluginDir"
}

Write-Host ""
Write-Host "=== MKM Clinic LOI Figma Plugin (one run) ===" -ForegroundColor Cyan
Write-Host "REST Variables API blocked on Starter; use Plugin API."
Write-Host ""
Write-Host "1) Open Figma file: $figmaUrl"
Write-Host "2) Plugins -> Development -> Import plugin from manifest..."
Write-Host "3) Select folder: $pluginDir"
Write-Host "4) Plugins -> Development -> MKM Clinic LOI Token Import -> Run"
Write-Host ""
Write-Host "Run once: 15 variables + 11 color styles + reference frame"
Write-Host ""

Set-Clipboard -Value $pluginDir
Start-Process $figmaUrl
explorer.exe $pluginDir

& py (Join-Path $root "scripts/probe_figma_variables_post_v1.py")

exit 0
