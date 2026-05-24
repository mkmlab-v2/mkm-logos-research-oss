#Requires -Version 5.1
<#
.SYNOPSIS
  Evolution allowlist check + general prophecy evolution health refresh (one shot).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$StrictAllowlist
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $root

$strictArgs = @()
if ($StrictAllowlist) { $strictArgs += "--strict" }

Write-Host "==> check_evolution_auto_apply_allowlist_v1.py" -ForegroundColor Cyan
& py scripts/check_evolution_auto_apply_allowlist_v1.py @strictArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> build_general_prophecy_evolution_health_v1.py" -ForegroundColor Cyan
& py scripts/build_general_prophecy_evolution_health_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] Evolution allowlist + health refresh complete." -ForegroundColor Green
