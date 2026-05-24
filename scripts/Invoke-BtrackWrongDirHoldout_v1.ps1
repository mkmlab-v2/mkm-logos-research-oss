#Requires -Version 5.1
<#
.SYNOPSIS
  Full wrong_dir holdout: 30d+180d dump, grids, advisory manifest (research only).
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

py scripts\run_btrack_wrong_dir_holdout_v1.py full
if ($LASTEXITCODE -ne 0) { throw "holdout full run exit $LASTEXITCODE" }

Write-Host "[OK] wrong_dir holdout full pipeline complete" -ForegroundColor Green
