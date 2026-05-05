<#
.SYNOPSIS
  Weekly A-Track 관제: Go/No-Go JSON 생성 + Slack 알림 전송.

.DESCRIPTION
  Fail-safe policy:
  - 시스템 에러/입력 누락은 기본 NO_GO
  - try/catch로 Slack 알림 실패도 로컬 로그로 남기고 종료

  기본 실행 순서:
  1) build_a_track_go_nogo_status.py (생성)
  2) send_a_track_go_nogo_slack.py (알림)

.PARAMETER OnSystemError
  no_go | hold_s1

.PARAMETER DryRun
  webhook 전송을 스킵하고 delivery log만 기록

.PARAMETER SkipClaimGuard
  외부 메시지 클레임 가드 선검사를 건너뜀(기본: 실행)

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\run_a_track_weekly_check.ps1
#>

param(
    [ValidateSet("no_go", "hold_s1")]
    [string]$OnSystemError = "no_go",
    [switch]$DryRun,
    [switch]$SkipClaimGuard
)

$ErrorActionPreference = "Stop"

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $workspaceRoot

$statusScript = Join-Path $workspaceRoot 'scripts\\build_a_track_go_nogo_status.py'
$slackScript = Join-Path $workspaceRoot 'scripts\\send_a_track_go_nogo_slack.py'
$claimGuardScript = Join-Path $workspaceRoot 'scripts\\build_external_message_claim_guard_report_v1.py'

if (-not (Test-Path -LiteralPath $statusScript)) {
    throw "Missing status builder script: $statusScript"
}
if (-not (Test-Path -LiteralPath $slackScript)) {
    throw "Missing slack sender script: $slackScript"
}

if (-not $SkipClaimGuard) {
    if (-not (Test-Path -LiteralPath $claimGuardScript)) {
        throw "Missing external message claim guard script: $claimGuardScript"
    }
    Write-Host "[a-track-weekly] Run external message claim guard..." -ForegroundColor Cyan
    & py -u $claimGuardScript
    if ($LASTEXITCODE -ne 0) {
        throw "build_external_message_claim_guard_report_v1.py failed with exit code $LASTEXITCODE"
    }

    $claimGuardReport = Join-Path $workspaceRoot 'docs\\final\\artifacts\\external_message_claim_guard_latest.json'
    if (-not (Test-Path -LiteralPath $claimGuardReport)) {
        throw "Missing claim guard report: $claimGuardReport"
    }
    $claimGuardJson = Get-Content -LiteralPath $claimGuardReport -Raw | ConvertFrom-Json
    $claimGuardStatus = $claimGuardJson.summary.status
    Write-Host "[a-track-weekly] claim guard status: $claimGuardStatus" -ForegroundColor DarkCyan
    if ($claimGuardStatus -ne "pass") {
        throw "external_message_claim_guard status is '$claimGuardStatus' (expected 'pass')"
    }
}

Write-Host "[a-track-weekly] Build status JSON (OnSystemError=$OnSystemError)..." -ForegroundColor Cyan
& py -u $statusScript --on-system-error $OnSystemError
if ($LASTEXITCODE -ne 0) {
    throw "build_a_track_go_nogo_status.py failed with exit code $LASTEXITCODE"
}

Write-Host "[a-track-weekly] Send Slack notification..." -ForegroundColor Cyan
if ($DryRun) {
    & py -u $slackScript --dry-run
} else {
    & py -u $slackScript
}
if ($LASTEXITCODE -ne 0) {
    throw "send_a_track_go_nogo_slack.py failed with exit code $LASTEXITCODE"
}

Write-Host "[a-track-weekly] Done." -ForegroundColor Green
exit 0

