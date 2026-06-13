#Requires -Version 5.1
<#
.SYNOPSIS
  Open account Logpush UI (Tier 3). Tries multiple dashboard routes (CF UI changes often).

  Manual if 404: Account home -> Observe/분석 -> Logs -> Logpush tab
#>
$ErrorActionPreference = "Stop"
$accountId = "646e42cf881ab43043c32430e99d9af4"
# NOTE: ?to=/:account/logs often infinite-loads in KR UI — open /home first, navigate manually.
$candidates = @(
    "https://dash.cloudflare.com/home",
    "https://dash.cloudflare.com/$accountId",
    "https://dash.cloudflare.com/$accountId/logs"
)
Write-Host "Opening Logpush routes (try in order if 404):" -ForegroundColor Cyan
foreach ($u in $candidates) { Write-Host "  $u" }
Write-Host ""
Write-Host "AVOID (infinite loading): https://dash.cloudflare.com/?to=/:$accountId/logs" -ForegroundColor Red
Write-Host ""
Write-Host "Manual navigation (Korean UI):" -ForegroundColor Yellow
Write-Host "  1) https://dash.cloudflare.com/home -> 본인 계정 선택"
Write-Host "  2) 왼쪽 메뉴: 분석 및 로그(Analytics & Logs) -> 로그(Logs)"
Write-Host "  3) 상단 Logpush 탭 -> Add Logpush job"
Write-Host "  4) Dataset: Turnstile Events | Destination: R2 | Bucket: mkm-turnstile-logs"
Write-Host ""
if ($env:OS -match "Windows") {
    Start-Process $candidates[0]
}
