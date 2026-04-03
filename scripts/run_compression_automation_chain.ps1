param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipHydrationMix,
    [switch]$SkipCompressionAlarm
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

Write-Host "=== run_ultra_compression_default.py ===" -ForegroundColor Cyan
py scripts\run_ultra_compression_default.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== report_ultra_compression_kpi_summary.py ===" -ForegroundColor Cyan
py scripts\report_ultra_compression_kpi_summary.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipHydrationMix) {
    Write-Host "=== report_token_api_hydration_mix.py ===" -ForegroundColor Cyan
    py scripts\report_token_api_hydration_mix.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[run_compression_automation_chain] OK" -ForegroundColor Green

$alarmScript = Join-Path $PSScriptRoot "send_compression_kpi_alarm_if_needed.ps1"
$null = & $alarmScript -WorkspaceRoot $WorkspaceRoot -SkipCompressionAlarm:$SkipCompressionAlarm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

exit 0
