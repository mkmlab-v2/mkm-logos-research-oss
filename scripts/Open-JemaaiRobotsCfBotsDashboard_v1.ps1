#Requires -Version 5.1
<#
.SYNOPSIS
  Open Cloudflare dashboard: jemaai.cloud → Security → Bots (managed robots.txt / AI crawlers).
  Tier 3 human: toggle OFF "Instruct AI bot traffic with robots.txt" then verify:
    py -c "import urllib.request; b=urllib.request.urlopen('https://jemaai.cloud/robots.txt').read().decode(); print('Disallow: /legacy/' in b)"
#>
$ErrorActionPreference = "Stop"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$zone = "jemaai.cloud"
$url = "https://dash.cloudflare.com/$accountId/$zone/security/settings?bots=true"
Write-Host "Open CF Bots settings (managed robots.txt OFF):" -ForegroundColor Cyan
Write-Host $url
Write-Host ""
Write-Host "Toggle OFF: Instruct AI bot traffic with robots.txt / AI Scrapers robots" -ForegroundColor Yellow
Write-Host "Then run: py scripts/setup_cloudflare_jemaai_robots_legacy_v1.py --skip-cf" -ForegroundColor DarkGray
if ($env:OS -match "Windows") { Start-Process $url }
