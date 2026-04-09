param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipHydrationMix,
    [switch]$SkipCompressionAlarm,
    [switch]$IncludeLiteralTrack,
    [switch]$IncludeUltraLiteralTrack
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

Write-Host "=== run_ultra_compression_default.py (universal) ===" -ForegroundColor Cyan
py scripts\run_ultra_compression_default.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($IncludeLiteralTrack) {
    Write-Host "=== run_ultra_compression_default.py --mode literal ===" -ForegroundColor Cyan
    py scripts\run_ultra_compression_default.py --mode literal
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($IncludeUltraLiteralTrack) {
    Write-Host "=== run_ultra_compression_default.py --mode ultra-literal (research) ===" -ForegroundColor Cyan
    py scripts\run_ultra_compression_default.py --mode ultra-literal
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "=== report_ultra_compression_kpi_summary.py ===" -ForegroundColor Cyan
py scripts\report_ultra_compression_kpi_summary.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipHydrationMix) {
    Write-Host "=== report_token_api_hydration_mix.py ===" -ForegroundColor Cyan
    py scripts\report_token_api_hydration_mix.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "=== report_compression_jaccard_loss_patterns.py (universal) ===" -ForegroundColor Cyan
py scripts\report_compression_jaccard_loss_patterns.py --sla-track universal
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($IncludeLiteralTrack) {
    Write-Host "=== report_compression_jaccard_loss_patterns.py (literal) ===" -ForegroundColor Cyan
    py scripts\report_compression_jaccard_loss_patterns.py --sla-track literal
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($IncludeUltraLiteralTrack) {
    Write-Host "=== report_compression_jaccard_loss_patterns.py (ultra_literal) ===" -ForegroundColor Cyan
    py scripts\report_compression_jaccard_loss_patterns.py --sla-track ultra_literal
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[run_compression_automation_chain] OK" -ForegroundColor Green

$alarmScript = Join-Path $PSScriptRoot "send_compression_kpi_alarm_if_needed.ps1"
$null = & $alarmScript -WorkspaceRoot $WorkspaceRoot -SkipCompressionAlarm:$SkipCompressionAlarm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

exit 0
