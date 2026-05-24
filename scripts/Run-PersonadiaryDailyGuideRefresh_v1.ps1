#Requires -Version 5.1
<#
.SYNOPSIS
  Rebuild commander daily fortune + PersonaDiary package + public JSON mirror.

.DESCRIPTION
  Chain: build_commander_daily_fortune_v1.py -> personadiary package (auto in fortune script).
  Use before no1kmedi build/deploy or local dev.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipRegenerate,
    [switch]$FortuneOnly
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$refreshArgs = @("scripts\refresh_personadiary_profile_packages_v1.py", "--report-json", "reports\personadiary_profile_refresh_latest.json")
if ($SkipRegenerate) { $refreshArgs += "--skip-regenerate" }

py @refreshArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($FortuneOnly) {
    Write-Host "[DONE] profile packages refreshed (fortune per registry)" -ForegroundColor Green
    exit 0
}

Write-Host "[DONE] personadiary profile packages -> public/data" -ForegroundColor Green
Write-Host "  registry:  data\personadiary\profile_registry_v1.json"
Write-Host "  default:   projects\no1kmedi\public\data\personadiary_daily_response_package_v1.json"
Write-Host "  profiles:  projects\no1kmedi\public\data\profiles\*.json"
