<#
.SYNOPSIS
  Cloudflare: jema-ai.com DNS for logos.jema-ai.com (token OR direct CNAME record).

.PARAMETER OpenDnsRecords
  Open zone DNS records (fastest path — add CNAME logos → app.jema-ai.com proxied).

.PARAMETER OpenTokenUi
  Open API token UI to create MKM_CLOUDFLARE_JEMA_AI_DNS_TOKEN.
#>
param(
    [switch]$OpenDnsRecords,
    [switch]$OpenTokenUi
)

$ErrorActionPreference = "Stop"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$zoneId = "e64f17593ce48e31c2839b421c8bd4c0"
$zoneName = "jema-ai.com"

if (-not $OpenTokenUi) { $OpenDnsRecords = $true }

if ($OpenDnsRecords) {
    $dnsUrl = "https://dash.cloudflare.com/$accountId/$zoneName/dns/records"
    Write-Host "=== logos.jema-ai.com DNS (1 record) ===" -ForegroundColor Cyan
    Write-Host "CNAME | Name: logos | Target: app.jema-ai.com | Proxied: ON"
    Write-Host $dnsUrl
    if ($env:OS -match "Windows") { Start-Process $dnsUrl }
}

if ($OpenTokenUi) {
    $tokName = [uri]::EscapeDataString("MKM-jema-ai-dns-logos-v1")
    $tokUrl = "https://dash.cloudflare.com/profile/api-tokens?accountId=$accountId&zoneId=$zoneId&name=$tokName"
    Write-Host ""
    Write-Host "=== API token (optional automation) ===" -ForegroundColor Cyan
    Write-Host "Permissions: Zone DNS Read + DNS Edit on jema-ai.com only"
    Write-Host "Paste -> reports\cloudflare_jema_ai_logos_dns_token_secret_LOCAL.json"
    Write-Host "Then: powershell -File scripts\Invoke-ApplyJemaAiLogosDnsTokenFromSecret_v1.ps1"
    Write-Host $tokUrl
    if ($env:OS -match "Windows") { Start-Process $tokUrl }
}

Write-Host ""
Write-Host "After save: powershell -File scripts\Invoke-LogosJemaAiDnsAuto_v1.ps1 -SkipOpenBrowser" -ForegroundColor Yellow
