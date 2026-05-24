#Requires -Version 5.1
<#
.SYNOPSIS
  Conditional gate matrix: 30d sweep + 180d OOS on top candidates (research only).
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

py scripts\run_btrack_conditional_gate_matrix_v1.py --also-180d
if ($LASTEXITCODE -ne 0) { throw "gate matrix exit $LASTEXITCODE" }

Write-Host "[OK] Conditional gate matrix complete" -ForegroundColor Green
