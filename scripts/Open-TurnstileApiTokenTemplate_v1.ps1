#Requires -Version 5.1
<#
.SYNOPSIS
  Open Cloudflare API token UI for Turnstile widget management (Account Turnstile Edit).
  After create: set CLOUDFLARE_TURNSTILE_API_TOKEN in .env or reports/cloudflare_turnstile_jema_ai_secret_LOCAL.json
  Then: py scripts/provision_turnstile_jema_ai_widget_v1.py
#>
$ErrorActionPreference = "Stop"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$name = [uri]::EscapeDataString("MKM-turnstile-jema-ai-v1")
$url = "https://dash.cloudflare.com/profile/api-tokens?accountId=$accountId&name=$name"
Write-Host "Opening CF API token UI (Turnstile Edit required):" -ForegroundColor Cyan
Write-Host $url
Write-Host ""
Write-Host "Permissions (Account group):" -ForegroundColor Yellow
Write-Host "  - Turnstile Sites Write (or Account Turnstile Edit)"
Write-Host "Account Resources: Include -> this account"
Write-Host ""
Write-Host "After paste token:" -ForegroundColor Yellow
Write-Host "  py scripts/provision_turnstile_jema_ai_widget_v1.py"
if ($env:OS -match "Windows") {
    Start-Process $url
} else {
    Write-Host "Open the URL above in your browser."
}
