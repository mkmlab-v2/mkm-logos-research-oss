# Serve .showroom_staging over HTTP so Trust visualization v0 can fetch JSON (file:// blocks fetch).
# Prereq: pwsh … deploy_showroom_static.ps1 (from windows-rehearsal) to populate staging.
# Usage: pwsh -File scripts/serve_showroom_trust_visualization_staging.ps1 [-Port 8792] [-Bind 127.0.0.1]
# Open: http://127.0.0.1:<Port>/public_showroom_trust_visualization_v0.html

param(
    [int] $Port = 8792,
    [string] $Bind = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = (Get-Item -LiteralPath $PSScriptRoot).Parent.FullName
$staging = Join-Path $workspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\.showroom_staging"
if (-not (Test-Path -LiteralPath $staging)) {
    throw "Staging folder missing: $staging — run deploy_showroom_static.ps1 first."
}

Set-Location -LiteralPath $staging
$url = "http://${Bind}:${Port}/public_showroom_trust_visualization_v0.html"
Write-Host "Staging: $staging"
Write-Host "Trust viz v0: $url"
Write-Host "Minimal board: http://${Bind}:${Port}/public_showroom_board_minimal.html"
Write-Host "Stop: Ctrl+C"
& py -m http.server $Port --bind $Bind
