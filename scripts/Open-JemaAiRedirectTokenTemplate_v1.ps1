#Requires -Version 5.1
<#
.SYNOPSIS
  Open Cloudflare API token UI for jema-ai.com dynamic redirect (Zone Read + Zone Rulesets).
  After create/edit: paste into reports/cloudflare_jema_ai_redirect_token_secret_LOCAL.json then:
    powershell -File scripts/Invoke-ApplyJemaAiRedirectTokenFromSecret_v1.ps1
#>
$ErrorActionPreference = "Stop"
$zoneId = "e64f17593ce48e31c2839b421c8bd4c0"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$name = [uri]::EscapeDataString("MKM-jema-ai-redirect-smartfarm-v1")
$url = "https://dash.cloudflare.com/profile/api-tokens?accountId=$accountId&zoneId=$zoneId&name=$name"
Write-Host "Opening CF token UI for jema-ai.com redirect (smartfarm 1-hop):" -ForegroundColor Cyan
Write-Host $url
Write-Host ""
Write-Host "Preferred: EDIT existing CLOUDFLARE_RULESETS_API_TOKEN — add jema-ai.com + Zone Read + Zone Rulesets" -ForegroundColor Yellow
Write-Host "Do NOT rotate CLOUDFLARE_API_TOKEN (DNS/mkmlife)." -ForegroundColor Yellow
if ($env:OS -match "Windows") {
    Start-Process $url
} else {
    Write-Host "Open the URL above in your browser."
}
Write-Host "Secret: reports\cloudflare_jema_ai_redirect_token_secret_LOCAL.json" -ForegroundColor Yellow
Write-Host '{ "MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN": "<paste>" }' -ForegroundColor Yellow
