#Requires -Version 5.1
<#
.SYNOPSIS
  Purge Cloudflare edge cache for jema-ai.com and jemaai.cloud (recommended after hub deploy).

.DESCRIPTION
  Requires CLOUDFLARE_API_TOKEN with Zone · Cache Purge (DNS-only tokens fail with HTTP 401).
  Writes reports/cloudflare_cache_purge_latest.json. On failure, prints manual dashboard steps.

.PARAMETER WhatIfOnly
  Print zones and token presence only; do not call API.
#>
param(
    [switch]$WhatIfOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py = Join-Path $PSScriptRoot "purge_cloudflare_cache_zones_v1.py"

foreach ($k in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN")) {
    if (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($k, "User"))) { break }
    if (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($k, "Process"))) { break }
}

$dotenv = Join-Path $root ".env"
if (Test-Path -LiteralPath $dotenv) {
    Get-Content -LiteralPath $dotenv -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line.Length -eq 0 -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $name = $line.Substring(0, $eq).Trim()
        $val = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
        if ($name -in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN") -and $val.Length -gt 0) {
            if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("CLOUDFLARE_API_TOKEN", "Process"))) {
                [Environment]::SetEnvironmentVariable("CLOUDFLARE_API_TOKEN", $val, "Process")
            }
        }
    }
}

$tok = [Environment]::GetEnvironmentVariable("CLOUDFLARE_API_TOKEN", "Process")
if ([string]::IsNullOrWhiteSpace($tok)) {
    $tok = [Environment]::GetEnvironmentVariable("CLOUDFLARE_API_TOKEN", "User")
}

if ($WhatIfOnly) {
    Write-Host "CLOUDFLARE_API_TOKEN set: $(-not [string]::IsNullOrWhiteSpace($tok))" -ForegroundColor Cyan
    Write-Host "Zones: jema-ai.com, jemaai.cloud (see purge_cloudflare_cache_zones_v1.py)" -ForegroundColor Cyan
    exit 0
}

if ([string]::IsNullOrWhiteSpace($tok)) {
    Write-Host "CLOUDFLARE_API_TOKEN missing. Set User env or root .env, then re-run." -ForegroundColor Red
    Write-Host "Manual: Cloudflare Dashboard -> each zone -> Caching -> Purge Everything" -ForegroundColor Yellow
    exit 1
}

$env:MKM_WORKSPACE_ROOT = $root
& py $py
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Host ""
    Write-Host "API purge failed (often 401 = token lacks Cache Purge permission)." -ForegroundColor Yellow
    Write-Host "Recommended manual:" -ForegroundColor Yellow
    Write-Host "  1. dash.cloudflare.com -> jema-ai.com -> Caching -> Purge Everything" -ForegroundColor Yellow
    Write-Host "  2. Same for jemaai.cloud" -ForegroundColor Yellow
    Write-Host "  3. Browser: app.jema-ai.com hard refresh (Ctrl+Shift+R)" -ForegroundColor Yellow
    Write-Host "Optional: create API token with Zone.Cache Purge + include both zones." -ForegroundColor Yellow
}
exit $code
