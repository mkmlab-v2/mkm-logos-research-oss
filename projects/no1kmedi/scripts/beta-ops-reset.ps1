<#
.SYNOPSIS
  MKMLIFE 베타 사용량 리셋 — POST /api/guardian/beta-ops/status

.PARAMETER Action
  reset_today | reset_identity

.PARAMETER Identity
  reset_identity 시 필수. 예: code:FRIENDS2026 또는 이메일

.PARAMETER DateUtc
  선택. YYYY-MM-DD (UTC 기준 날짜 키). 기본: 오늘 UTC.

.EXAMPLE
  pwsh -File scripts/beta-ops-reset.ps1 -Action reset_today
.EXAMPLE
  pwsh -File scripts/beta-ops-reset.ps1 -Action reset_identity -Identity 'code:FRIENDS2026'
#>
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("reset_today", "reset_identity")]
  [string] $Action,

  [string] $Identity = "",
  [string] $DateUtc = "",
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

if ($Action -eq "reset_identity" -and (-not $Identity -or $Identity.Trim() -eq "")) {
  Write-Error "reset_identity requires -Identity (e.g. code:FRIENDS2026 or email)."
  exit 1
}

$body = @{ action = $Action }
if ($Identity.Trim() -ne "") { $body.identity = $Identity.Trim() }
if ($DateUtc.Trim() -ne "") { $body.date_utc = $DateUtc.Trim() }

$uri = "$BaseUrl/api/guardian/beta-ops/status"
$headers = @{ Authorization = "Bearer $Token" }

try {
  $json = $body | ConvertTo-Json -Compress
  $result = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $json -ContentType "application/json; charset=utf-8"
  $result | ConvertTo-Json -Depth 10
} catch {
  Write-Error $_
  exit 1
}
