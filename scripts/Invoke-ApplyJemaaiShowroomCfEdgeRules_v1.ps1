#Requires -Version 5.1
<#
.SYNOPSIS
  Check CF rules token -> apply jemaai showroom edge rules -> autoverify (no duplicate apply).
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[cf-edge] 1/3 token roles triage..." -ForegroundColor Cyan
py scripts/check_cloudflare_token_roles_v1.py 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host "[cf-edge] STOP: py scripts/check_cloudflare_token_roles_v1.py — reports/cloudflare_token_roles_triage_v1_latest.json recurrence_guard" -ForegroundColor Yellow
    Write-Host "[cf-edge] NOT 'create new token daily' — set CLOUDFLARE_RULESETS_API_TOKEN once or manual dashboard." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "[cf-edge] 2/3 apply rules..." -ForegroundColor Cyan
py scripts/apply_jemaai_cloud_showroom_cf_edge_rules_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[cf-edge] 3/3 autoverify..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-JemaaiShowroomEdgeAutoverify_v1.ps1 -SkipApply -SkipVpsSync
exit $LASTEXITCODE
