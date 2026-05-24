#Requires -Version 5.1
<#
.SYNOPSIS
  Cloudflare Email Routing: forward support@mkmlife.com (default) without Hostinger Email.

.DESCRIPTION
  권장 운영 순서(대시보드와 동일; API는 토큰 권한이 있을 때만 자동화):
  1) 이메일 라우팅 → 대상 주소: MKM_MKMLIFE_SUPPORT_FORWARD_TO(기본 admin@no1kmedi.com) 검증 완료까지.
  2) 라우팅 규칙: 사용자 설정 주소 support → 이메일로 보내기 → 검증된 대상 선택 → 저장.
  3) 선택: 본 스크립트로 재현·감사(reports/cloudflare_email_routing_setup_latest.json). DNS 전용 토큰으로는 403.

.PARAMETER Apex
  Zone apex (default mkmlife.com).

.PARAMETER LocalPart
  Mailbox local part (default support).

.PARAMETER ForwardTo
  Destination inbox. Default: env MKM_MKMLIFE_SUPPORT_FORWARD_TO or admin@no1kmedi.com.

.PARAMETER ZoneId
  Optional zone id when token cannot list zones?name=.

.PARAMETER UseMkmlifeFixtureZoneId
  If set and ZoneId is empty, read zone_id from scripts/data/hostinger_full_exit/mkmlife_cloudflare_zone_v1.json (operator must confirm id matches dashboard).

.PARAMETER DryRun
  Resolve zone + read routing state only (no mutations).

.NOTES
  권장안: CF Email Routing MX 유지. Hostinger 웹메일과 apex 병행 불가(의도적 이전 시 Hostinger 알림 무시 가능). 상세: docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md 절 1.3.
  Exit: 0 OK/이미 있음 · 2 zone 미가시 · 3 routing GET/enable 실패 · 4 대상 생성 실패 · 5 대상 미검증 · 6 규칙 생성 실패 · 7 account_id 없음.
  Report: reports/cloudflare_email_routing_setup_latest.json (blocked 시 manual 배열 참고)
#>
param(
    [string]$Apex = "mkmlife.com",
    [string]$LocalPart = "support",
    [string]$ForwardTo = "",
    [string]$ZoneId = "",
    [switch]$UseMkmlifeFixtureZoneId,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if ($UseMkmlifeFixtureZoneId -and [string]::IsNullOrWhiteSpace($ZoneId)) {
    $fixture = Join-Path $PSScriptRoot "data\hostinger_full_exit\mkmlife_cloudflare_zone_v1.json"
    if (-not (Test-Path -LiteralPath $fixture)) { throw "Missing fixture: $fixture" }
    $j = Get-Content -LiteralPath $fixture -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($j.zone_id)) { throw "fixture.zone_id empty in $fixture" }
    $ZoneId = [string]$j.zone_id
}

$py = Join-Path $PSScriptRoot "setup_cloudflare_email_routing_v1.py"
if (-not (Test-Path -LiteralPath $py)) { throw "Missing $py" }

$argsList = @(
    $py,
    "--apex", $Apex,
    "--local-part", $LocalPart
)
if (-not [string]::IsNullOrWhiteSpace($ForwardTo)) {
    $argsList += @("--forward-to", $ForwardTo.Trim())
}
if (-not [string]::IsNullOrWhiteSpace($ZoneId)) {
    $argsList += @("--zone-id", $ZoneId.Trim())
}
if ($DryRun) { $argsList += "--dry-run" }

& py @argsList
exit $LASTEXITCODE
