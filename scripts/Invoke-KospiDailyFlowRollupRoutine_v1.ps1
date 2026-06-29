#Requires -Version 5.1
<#
.SYNOPSIS
  Apply optional pending daily flow row, rollup monthly CSV, refresh miss×flow probe [HYPO].

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-KospiDailyFlowRollupRoutine_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath $WorkspaceRoot
Set-Location -LiteralPath $root

$pending = Join-Path $root "research\market_data\kospi_daily_flow_pending_row_v1.json"
if (Test-Path -LiteralPath $pending) {
    Write-Host "==> apply_kospi_daily_flow_pending_row_v1.py"
    py scripts/apply_kospi_daily_flow_pending_row_v1.py
    if ($LASTEXITCODE -ne 0) { throw "apply pending flow exit $LASTEXITCODE" }
} else {
    Write-Host "SKIP pending flow (no $pending)"
}

Write-Host "==> audit_kospi_daily_flow_gaps_v1.py (May gap report)"
py scripts/audit_kospi_daily_flow_gaps_v1.py --from-date 2026-05-01 --to-date 2026-05-31
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> rollup_kospi_monthly_flow_from_daily_v1.py"
py scripts/rollup_kospi_monthly_flow_from_daily_v1.py
if ($LASTEXITCODE -ne 0) { throw "rollup exit $LASTEXITCODE" }

Write-Host "==> build_kospi_prophecy_miss_flow_probe_v1.py"
py scripts/build_kospi_prophecy_miss_flow_probe_v1.py
if ($LASTEXITCODE -ne 0) { throw "miss flow probe exit $LASTEXITCODE" }

Write-Host "OK KospiDailyFlowRollupRoutine"
