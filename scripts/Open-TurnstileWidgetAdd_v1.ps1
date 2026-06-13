#Requires -Version 5.1
<#
.SYNOPSIS
  Open Turnstile widget add UI (Tier 3 Human Chrome). Prefer API:
    py scripts/provision_turnstile_jema_ai_widget_v1.py
#>
$ErrorActionPreference = "Stop"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$url = "https://dash.cloudflare.com/$accountId/turnstile/add"
Write-Host "Opening Turnstile add UI (Human Chrome — agent login forbidden):" -ForegroundColor Cyan
Write-Host $url
Write-Host ""
Write-Host "Recommended hostnames:" -ForegroundColor Yellow
Write-Host "  jema-ai.com"
Write-Host "  app.jema-ai.com"
Write-Host "  www.jema-ai.com"
Write-Host "Mode: Managed"
if ($env:OS -match "Windows") {
    Start-Process $url
} else {
    Write-Host "Open the URL above in your browser."
}
