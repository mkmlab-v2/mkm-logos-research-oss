#Requires -Version 5.1
<#
.SYNOPSIS
  Extend existing CLOUDFLARE_RULESETS_API_TOKEN: add Zone Bot Management Edit on jemaai.cloud.
  Opens CF API token edit UI — paste updated token to reports/cloudflare_jemaai_solo_edge_token_secret_LOCAL.json
  then: powershell -File scripts\Invoke-ApplyJemaaiRobotsBotManagement_v1.ps1
#>
$ErrorActionPreference = "Stop"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$url = "https://dash.cloudflare.com/profile/api-tokens"
Write-Host "Edit existing jemaai rulesets token — add permissions:" -ForegroundColor Cyan
Write-Host "  Zone · jemaai.cloud · Bot Management Edit (+ Cache Purge optional)" -ForegroundColor Yellow
Write-Host $url
Write-Host ""
Write-Host "After save, update reports\cloudflare_jemaai_solo_edge_token_secret_LOCAL.json" -ForegroundColor DarkGray
Write-Host "Run: powershell -File scripts\Invoke-ApplyJemaaiRobotsBotManagement_v1.ps1" -ForegroundColor Green
if ($env:OS -match "Windows") { Start-Process $url }
