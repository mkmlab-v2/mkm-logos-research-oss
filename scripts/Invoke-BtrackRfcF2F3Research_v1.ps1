#Requires -Version 5.1
<#
.SYNOPSIS
  RFC F2/F3: 30d experiment + 180d OOS gate (research only; no ensemble write).
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "==> [1/2] RFC F2/F3 30d experiment" -ForegroundColor Cyan
py scripts\run_btrack_rfc_f2_f3_experiment_v1.py
if ($LASTEXITCODE -ne 0) { throw "f2 f3 30d exit $LASTEXITCODE" }

Write-Host "==> [2/2] RFC F2/F3 180d OOS" -ForegroundColor Cyan
py scripts\run_btrack_rfc_f2_f3_oos_180d_v1.py
if ($LASTEXITCODE -ne 0) { throw "f2 f3 180d exit $LASTEXITCODE" }

Write-Host "[OK] RFC F2/F3 research complete" -ForegroundColor Green
