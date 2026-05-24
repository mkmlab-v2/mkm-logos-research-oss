#Requires -Version 5.1
<#
.SYNOPSIS
  B-track prophecy KPI vs VPS/live trading PnL — side-by-side separation report (no causality).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
& py scripts\build_btrack_vps_pnl_separation_report_v1.py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
