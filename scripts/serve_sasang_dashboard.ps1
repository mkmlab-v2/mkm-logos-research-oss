# Serve workspace root over HTTP so the Sasang B-track dashboard can be opened at a live URL.
# Usage: pwsh -File scripts/serve_sasang_dashboard.ps1 [-Port 8765]
# Then: http://localhost:<Port>/docs/final/artifacts/sasang_dynamics_proxy_widget_v1.html

param(
    [int] $Port = 8765
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Get-Item -LiteralPath $PSScriptRoot).Parent.FullName
Set-Location -LiteralPath $workspaceRoot

$rel = 'docs/final/artifacts/sasang_dynamics_proxy_widget_v1.html'
$url = "http://127.0.0.1:${Port}/$($rel -replace '\\','/')"
Write-Host "Workspace: $workspaceRoot"
Write-Host "Open: $url"
Write-Host "Stop: Ctrl+C"
& py -m http.server $Port --bind 127.0.0.1
