#Requires -Version 5.1
<#
.SYNOPSIS
  Open CF API token UI for Turnstile Logpush + R2 (Tier 3 Human Chrome).

  After create, add to C:\workspace\.env:
    CLOUDFLARE_LOGPUSH_API_TOKEN=cfut_...

  Then:
    py scripts/provision_turnstile_logpush_r2_bundle_v1.py --apply
#>
$ErrorActionPreference = "Stop"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$name = [uri]::EscapeDataString("MKM-turnstile-logpush-r2-v1")
$url = "https://dash.cloudflare.com/profile/api-tokens?accountId=$accountId&name=$name"
Write-Host "Opening CF API token UI (Human Chrome):" -ForegroundColor Cyan
Write-Host $url
Write-Host ""
Write-Host "Custom token — Account permissions (minimum):" -ForegroundColor Yellow
Write-Host "  - Logs: Edit  (Logpush)"
Write-Host "  - Workers R2 Storage: Edit  (bucket + object write)"
Write-Host "  - (optional) Account API Tokens: Edit  (fully automated R2 sub-token)"
Write-Host "Account Resources: Include -> this account ($accountId)"
Write-Host ""
Write-Host "Save token as .env:" -ForegroundColor Yellow
Write-Host "  CLOUDFLARE_LOGPUSH_API_TOKEN=cfut_..."
Write-Host ""
Write-Host "Then run:" -ForegroundColor Yellow
Write-Host "  py scripts/provision_turnstile_logpush_r2_bundle_v1.py --apply"
if ($env:OS -match "Windows") { Start-Process $url }
