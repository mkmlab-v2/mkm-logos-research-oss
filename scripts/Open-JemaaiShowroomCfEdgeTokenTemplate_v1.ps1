#Requires -Version 5.1
<#
.SYNOPSIS
  Open Cloudflare Create Token UI for jemaai.cloud showroom rulesets (Zone Read + WAF Edit + Cache Rules Edit).
  After create: paste into reports/cloudflare_jemaai_solo_edge_token_secret_LOCAL.json then:
    powershell -File scripts\Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1
#>
$ErrorActionPreference = "Stop"
$zoneId = "cf557dfa09436d998416ad849e73c0ec"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$name = [uri]::EscapeDataString("MKM-jemaai-showroom-rulesets-v1")
# Cloudflare custom token UI (permission group keys vary; dashboard also allows manual pick per JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md)
$url = "https://dash.cloudflare.com/profile/api-tokens?accountId=$accountId&zoneId=$zoneId&name=$name"
Write-Host "Opening CF token UI for jemaai.cloud edge rules:" -ForegroundColor Cyan
Write-Host $url
Write-Host ""
Write-Host "STOP empty custom token if search shows nothing:" -ForegroundColor Yellow
Write-Host "  A) Edit existing token MKM-mkmlab-zone-settings-dns-v1 (Cache Rules + Zone WAF) for jemaai.cloud"
Write-Host "  B) Manual dashboard only - see JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md section dashboard table"
Write-Host "  C) Custom token: LEFT column = Zone GROUP (not zone name), then search WAF / Cache Rules / Account Rulesets"
if ($env:OS -match "Windows") {
    Start-Process $url
} else {
    Write-Host "Open the URL above in your browser."
}
Write-Host "Secret file (gitignored path): reports\cloudflare_jemaai_solo_edge_token_secret_LOCAL.json" -ForegroundColor Yellow
Write-Host 'JSON: { "CLOUDFLARE_RULESETS_API_TOKEN": "<paste>" }' -ForegroundColor Yellow
