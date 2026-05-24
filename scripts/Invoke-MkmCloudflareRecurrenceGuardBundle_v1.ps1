#Requires -Version 5.1
<#
.SYNOPSIS
  MKM Cloudflare 재발 방지 번들: 존 목록 갱신 → 토큰 triage → 존·HTTP 감사.
.NOTES
  Exit 0 = smartfarm 1-hop HTTP OK (operational SSOT) and/or full API ready.
  Exit 2 = blocking gap (HTTP or jemaai rulesets).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipInventoryRefresh
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }

Write-Host "[1/3] Cloudflare zone list (general token)..." -ForegroundColor Cyan
if (-not $SkipInventoryRefresh) {
    & $py scripts/list_cloudflare_zones_for_op5_v1.py
    if ($LASTEXITCODE -ne 0) { Write-Warning "zone inventory refresh exit $LASTEXITCODE" }
}

Write-Host "[2/3] Token roles triage..." -ForegroundColor Cyan
& $py scripts/check_cloudflare_token_roles_v1.py
$triageExit = $LASTEXITCODE

Write-Host "[3/3] Zone registry audit + HTTP probes..." -ForegroundColor Cyan
$auditArgs = @("scripts/audit_mkm_cloudflare_zones_v1.py")
if (-not $SkipInventoryRefresh) { $auditArgs += "--refresh-inventory" }
& $py @auditArgs
$auditExit = $LASTEXITCODE

Write-Host ""
Write-Host "Reports:" -ForegroundColor Green
Write-Host "  reports/cloudflare_op5_zone_inventory_v1.json"
Write-Host "  reports/cloudflare_token_roles_triage_v1_latest.json"
Write-Host "  reports/mkm_cloudflare_zone_audit_v1_latest.json"
Write-Host "SSOT: docs/final/artifacts/mkm_cloudflare_zone_registry_v1.json"

if ($auditExit -eq 0 -and $triageExit -eq 0) { exit 0 }
if ($auditExit -eq 2 -or $triageExit -eq 2) { exit 2 }
exit 1
