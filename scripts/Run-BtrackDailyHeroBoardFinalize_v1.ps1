#Requires -Version 5.1
<#
.SYNOPSIS
  Finalize daily hero board v1: chain + pytest + register + checkpoint.
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "[HeroBoardFinalize] 1 daily chain evening"
& $py scripts/run_btrack_daily_hero_board_chain_v1.py --phase evening
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[HeroBoardFinalize] 2 pytest"
& $py -m pytest tests/test_btrack_daily_hero_board_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[HeroBoardFinalize] 3 register scheduler (Disabled)"
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-BtrackDailyHeroBoardTask_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[HeroBoardFinalize] 4 checkpoint"
& $py scripts/athena_checkpoint.py "Hero board gap closure: Open-Meteo weather GT + flow/pre-news data refresh wired evening chain exit 0"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$report = @{
    schema = "btrack_daily_hero_board_finalize_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    ok = $true
    send_gate = "HOLD"
} | ConvertTo-Json
$out = Join-Path $WorkspaceRoot "reports\btrack_daily_hero_board_finalize_v1_latest.json"
$report | Set-Content -LiteralPath $out -Encoding utf8
Write-Host "[HeroBoardFinalize] DONE -> $out"
exit 0
