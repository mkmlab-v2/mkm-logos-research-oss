#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly: Track A + Track B literal compression automation, governance JSON, optional log line, KPI webhook alarm.

.DESCRIPTION
  1) run_compression_automation_chain.ps1 (universal + literal by default; -SkipLiteralTrack for Track A only)
  2) build_compression_weekly_governance_report.py
  3) append one line to reports/compression_weekly_governance_log.jsonl
  Alarms: send_compression_kpi_alarm_if_needed.ps1 is invoked from the automation chain unless -SkipCompressionAlarm.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipLiteralTrack,
    [switch]$SkipCompressionAlarm
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$auto = Join-Path $WorkspaceRoot "scripts\run_compression_automation_chain.ps1"
if (-not (Test-Path -LiteralPath $auto)) { throw "Missing: $auto" }

$autoArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $auto,
    "-WorkspaceRoot", $WorkspaceRoot
)
if (-not $SkipLiteralTrack) {
    $autoArgs += "-IncludeLiteralTrack"
}
if ($SkipCompressionAlarm) {
    $autoArgs += "-SkipCompressionAlarm"
}
& powershell @autoArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== build_compression_weekly_governance_report.py ===" -ForegroundColor Cyan
& py (Join-Path $WorkspaceRoot "scripts\build_compression_weekly_governance_report.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$logDir = Join-Path $WorkspaceRoot "reports"
$logPath = Join-Path $logDir "compression_weekly_governance_log.jsonl"
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
$line = (@{
    schema    = "compression_weekly_governance_log_v1"
    ts_utc    = $ts
    event     = "compression_weekly_governance_chain"
    exit_code = 0
    skip_literal_track = [bool]$SkipLiteralTrack
} | ConvertTo-Json -Compress -Depth 4)
Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
Write-Host "Appended: $logPath" -ForegroundColor DarkGray

Write-Host "[run_compression_weekly_governance_chain] OK" -ForegroundColor Green
exit 0
