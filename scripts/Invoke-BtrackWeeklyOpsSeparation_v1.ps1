#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly B-track ops: VPS/PnL separation vs prophecy KPI + headline miss snapshot (research/obs only).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$LogJsonl = "reports/btrack_weekly_ops_separation_log.jsonl"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$summary = [ordered]@{ ts_utc = $ts; steps = @() }

function Invoke-Step($name, [scriptblock]$block) {
    & $block
    if ($LASTEXITCODE -ne 0) { throw "$name exit $LASTEXITCODE" }
    $script:summary.steps += $name
}

Invoke-Step "vps_pnl_separation" {
    py scripts/build_btrack_vps_pnl_separation_report_v1.py --output reports/btrack_vps_pnl_separation_v1_latest.json
}
Invoke-Step "headline_miss" {
    py scripts/build_btrack_headline_miss_report_v1.py
}
Invoke-Step "neutral_attribution" {
    py scripts/analyze_btrack_neutral_attribution_v1.py
}
Invoke-Step "model_swap_harness_180d" {
    py scripts/run_btrack_model_swap_harness_v1.py --include-180d
}

$sep = Get-Content -LiteralPath "reports/btrack_vps_pnl_separation_v1_latest.json" -Raw | ConvertFrom-Json
$summary.observation_line = $sep.observation_line
$line = ($summary | ConvertTo-Json -Compress -Depth 6)
$logPath = Join-Path $WorkspaceRoot $LogJsonl
$logDir = Split-Path -Parent $logPath
if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
Write-Host "[OK] Weekly ops separation logged -> $LogJsonl" -ForegroundColor Green
if ($sep.observation_line) { Write-Host $sep.observation_line }
