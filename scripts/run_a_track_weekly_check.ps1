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

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\run_a_track_weekly_check.ps1
#>

param(
    [ValidateSet("no_go", "hold_s1")]
    [string]$OnSystemError = "no_go",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $workspaceRoot

$statusScript = Join-Path $workspaceRoot 'scripts\\build_a_track_go_nogo_status.py'
$slackScript = Join-Path $workspaceRoot 'scripts\\send_a_track_go_nogo_slack.py'

if (-not (Test-Path -LiteralPath $statusScript)) {
    throw "Missing status builder script: $statusScript"
}
if (-not (Test-Path -LiteralPath $slackScript)) {
    throw "Missing slack sender script: $slackScript"
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

