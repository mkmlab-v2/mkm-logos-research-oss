#Requires -Version 5.1
<#
.SYNOPSIS
  Open R2 bucket UI for Turnstile Logpush (Tier 3 Human Chrome).
  Recommended bucket name: mkm-turnstile-logs
#>
$ErrorActionPreference = "Stop"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$url = "https://dash.cloudflare.com/$accountId/r2/overview"
Write-Host "Opening R2 overview (create bucket: mkm-turnstile-logs):" -ForegroundColor Cyan
Write-Host $url
if ($env:OS -match "Windows") { Start-Process $url }
