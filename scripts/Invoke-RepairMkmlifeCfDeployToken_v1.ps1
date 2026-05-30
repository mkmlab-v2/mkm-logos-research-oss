#Requires -Version 5.1
<#
.SYNOPSIS
  Repair mkmlife CF deploy token — probe routes, auto-create if parent allows, else open dashboard template.
#>
param(
    [switch]$OpenDashboardOnly,
    [switch]$SkipApply
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

Write-Host "[repair-mkmlife-cf] probe deploy token (Workers Routes required for wrangler routes sync)" -ForegroundColor Cyan
$probeBefore = & py scripts\_probe_cf_mkmlife_deploy_token_v1.py 2>&1 | Out-String
Write-Host $probeBefore
if ($LASTEXITCODE -eq 0) {
    Write-Host "[repair-mkmlife-cf] OK — token already has Workers Routes Edit" -ForegroundColor Green
    exit 0
}

if ($OpenDashboardOnly) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Open-MkmlifeCloudflareDeployTokenTemplate_v1.ps1
    Write-Host "[repair-mkmlife-cf] Paste new token into reports\cloudflare_mkmlife_deploy_token_secret_LOCAL.json then:" -ForegroundColor Yellow
    Write-Host "  powershell -File scripts\Invoke-MkmlifeCfDeployTokenReadiness_v1.ps1 -ApplyIfPresent" -ForegroundColor Yellow
    exit 0
}

Write-Host "[repair-mkmlife-cf] try auto-create via parent token..." -ForegroundColor Cyan
& py scripts\try_create_cloudflare_mkmlife_deploy_token_v1.py
if ($LASTEXITCODE -eq 0 -and -not $SkipApply) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ApplyMkmlifeCfDeployTokenFromSecret_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $probeAfter = & py scripts\_probe_cf_mkmlife_deploy_token_v1.py 2>&1 | Out-String
    Write-Host $probeAfter
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[repair-mkmlife-cf] auto-create + apply OK" -ForegroundColor Green
        exit 0
    }
}

Write-Host "[repair-mkmlife-cf] auto-create unavailable — opening dashboard template (add Workers Routes Edit on mkmlife.com zone)" -ForegroundColor Yellow
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Open-MkmlifeCloudflareDeployTokenTemplate_v1.ps1
Write-Host @"
Next:
  1) Create OR edit token in dashboard (include Zone > Workers Routes > Edit for mkmlife.com)
  2) Paste into reports\cloudflare_mkmlife_deploy_token_secret_LOCAL.json
  3) powershell -File scripts\Invoke-MkmlifeCfDeployTokenReadiness_v1.ps1 -ApplyIfPresent
  4) py scripts\_probe_cf_mkmlife_deploy_token_v1.py  (expect workers_routes_list success=True)
"@ -ForegroundColor Cyan
exit 1
