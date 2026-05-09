<#
.SYNOPSIS
  MKMLIFE 베타 사용량 조회 — GET /api/guardian/beta-ops/status

.DESCRIPTION
  MKMLIFE_BETA_ADMIN_TOKEN 또는 NO1KMEDI_ADMIN_TOKEN 환경 변수로 인증합니다.
  기본 베이스 URL: http://127.0.0.1:3010 (next dev)

.PARAMETER BaseUrl
  예: https://mkmlife.com

.EXAMPLE
  pwsh -File scripts/beta-ops-status.ps1
.EXAMPLE
  $env:MKMLIFE_BETA_ADMIN_TOKEN='***'; pwsh -File scripts/beta-ops-status.ps1 -BaseUrl 'https://example.com'
#>
param(
  [string] $BaseUrl = $env:MKMLIFE_BETA_API_BASE_URL,
  [string] $Token = $env:MKMLIFE_BETA_ADMIN_TOKEN
)

$ErrorActionPreference = "Stop"

if (-not $BaseUrl -or $BaseUrl.Trim() -eq "") {
  $BaseUrl = $env:NO1KMEDI_BASE_URL
}
if (-not $BaseUrl -or $BaseUrl.Trim() -eq "") {
  $BaseUrl = "http://127.0.0.1:3010"
}
$BaseUrl = $BaseUrl.TrimEnd("/")

if (-not $Token -or $Token.Trim() -eq "") {
  $Token = $env:NO1KMEDI_ADMIN_TOKEN
}
if (-not $Token -or $Token.Trim() -eq "") {
  Write-Error "Set MKMLIFE_BETA_ADMIN_TOKEN or NO1KMEDI_ADMIN_TOKEN."
  exit 1
}

$uri = "$BaseUrl/api/guardian/beta-ops/status"
$headers = @{ Authorization = "Bearer $Token" }

try {
  $result = Invoke-RestMethod -Uri $uri -Method Get -Headers $headers -ContentType "application/json"
  $result | ConvertTo-Json -Depth 10
} catch {
  Write-Error $_
  exit 1
}
