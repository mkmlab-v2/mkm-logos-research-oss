#Requires -Version 5.1
<#
.SYNOPSIS
  O-P5: Apply jema12 www+apex /studio redirect via API; on 403 open CF token + rule pages.

.NOTES
  Optional automation only — O-P5 is already DONE if verify shows op5_pass=True (dashboard rule).
  Needs Rulesets Edit token only to replay via API; do not treat PUT 403 as incomplete O-P5.
#>
param(
    [switch]$SkipBrowserOpen,
    [string]$ZoneId = "a9f34634593eef57609e48c3ffbe6f24"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Get-RulesetsToken {
    foreach ($k in @("CLOUDFLARE_RULESETS_API_TOKEN", "CLOUDFLARE_API_TOKEN", "CF_API_TOKEN")) {
        foreach ($scope in @("Process", "User", "Machine")) {
            $v = [Environment]::GetEnvironmentVariable($k, $scope)
            if (-not [string]::IsNullOrWhiteSpace($v)) {
                return @{ Var = $k; Token = $v.Trim() }
            }
        }
    }
    $envPath = Join-Path $root ".env"
    if (Test-Path -LiteralPath $envPath) {
        foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
            if ($line -match '^\s*CLOUDFLARE_RULESETS_API_TOKEN=(.+)$') {
                return @{ Var = "CLOUDFLARE_RULESETS_API_TOKEN"; Token = $Matches[1].Trim().Trim('"').Trim("'") }
            }
        }
    }
    return $null
}

$tok = Get-RulesetsToken
if (-not $tok) {
    throw "Set CLOUDFLARE_RULESETS_API_TOKEN or CLOUDFLARE_API_TOKEN in User env or .env"
}

$env:CLOUDFLARE_API_TOKEN = $tok.Token
if ($tok.Var -eq "CLOUDFLARE_RULESETS_API_TOKEN") {
    $env:CLOUDFLARE_RULESETS_API_TOKEN = $tok.Token
}

Write-Host "== probe rulesets permission ==" -ForegroundColor Cyan
& py (Join-Path $root "scripts\probe_cloudflare_rulesets_permission_v1.py")
$probeExit = $LASTEXITCODE

Write-Host "== apply www+apex /studio redirect ==" -ForegroundColor Cyan
& py (Join-Path $root "scripts\setup_cloudflare_jema12_studio_oracle_redirect_v1.py") --zone-id $ZoneId
$applyExit = $LASTEXITCODE

if ($applyExit -eq 0) {
    Write-Host "== verify ==" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\verify_jema12_studio_oracle_redirect_v1.ps1")
    exit $LASTEXITCODE
}

if (-not $SkipBrowserOpen) {
    Write-Host ""
    Write-Host "API PUT skipped (Rulesets scope). If verify op5_pass=True, O-P5 is already DONE — no new token." -ForegroundColor Yellow
    Write-Host "Optional: open www redirect rule page only — reports/ms_rq019_paste_ready/op5_www_studio_redirect_manual.txt" -ForegroundColor Yellow
    Write-Host ""
    Start-Process "https://dash.cloudflare.com/$ZoneId/jema12.com/rules/redirect-rules"
}

exit $applyExit
