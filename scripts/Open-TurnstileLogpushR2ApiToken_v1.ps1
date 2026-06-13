#Requires -Version 5.1
<#
.SYNOPSIS
  Open R2 API token UI (scoped to mkm-turnstile-logs). Tier 3 Human Chrome.

  After create, add to C:\workspace\.env:
    MKM_R2_LOGPUSH_ACCESS_KEY_ID=...
    MKM_R2_LOGPUSH_SECRET_ACCESS_KEY=...

  Also need Logpush-capable token:
    CLOUDFLARE_LOGPUSH_API_TOKEN=cfut_...  (Account Logs Edit)

  Then:
    py scripts/provision_turnstile_logpush_r2_bundle_v1.py --assume-bucket-exists --apply
#>
$ErrorActionPreference = "Stop"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$url = "https://dash.cloudflare.com/$accountId/r2/api-tokens"
Write-Host "Opening R2 API tokens (bucket: mkm-turnstile-logs):" -ForegroundColor Cyan
Write-Host $url
Write-Host ""
Write-Host "Create token:" -ForegroundColor Yellow
Write-Host "  Permission: Object Read & Write"
Write-Host "  Scope: bucket mkm-turnstile-logs only"
Write-Host ""
Write-Host "Paste into .env:" -ForegroundColor Yellow
Write-Host "  MKM_R2_LOGPUSH_ACCESS_KEY_ID=<Access Key ID>"
Write-Host "  MKM_R2_LOGPUSH_SECRET_ACCESS_KEY=<Secret Access Key>"
if ($env:OS -match "Windows") { Start-Process $url }
