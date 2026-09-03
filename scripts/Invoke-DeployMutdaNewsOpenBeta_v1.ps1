#Requires -Version 5.1
<#
.SYNOPSIS
  Build → check → wrangler deploy for mutda-news-open-beta (OPEN_BETA only).

.NOTES
  Never prints secrets. Clears CLOUDFLARE_API_TOKEN from env before OAuth-style deploy
  only when -PreferOAuth is set; otherwise uses ambient auth without echoing values.
  PRODUCT_DONE is never claimed.
#>
param(
    [string]$RepoRoot = "C:\workspace",
    [string]$ProjectDir = "C:\workspace\projects\mutda-news-open-beta-v1",
    [switch]$SkipDeploy,
    [switch]$PreferOAuth
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $RepoRoot

Write-Host "[mutda-open-beta] build" -ForegroundColor Cyan
py scripts/build_mutda_news_open_beta_site_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[mutda-open-beta] check" -ForegroundColor Cyan
py scripts/check_mutda_news_open_beta_site_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SkipDeploy) {
    Write-Host "[mutda-open-beta] SkipDeploy — build+check only (PRODUCT_DONE=false)" -ForegroundColor Yellow
    exit 0
}

if ($PreferOAuth) {
    foreach ($k in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_RULESETS_API_TOKEN")) {
        if (Test-Path "Env:$k") {
            Remove-Item "Env:$k" -ErrorAction SilentlyContinue
        }
    }
}

if (-not (Test-Path -LiteralPath $ProjectDir)) {
    Write-Host "[mutda-open-beta] FAIL missing project dir" -ForegroundColor Red
    exit 2
}

Set-Location -LiteralPath $ProjectDir
Write-Host "[mutda-open-beta] wrangler deploy (secrets not printed)" -ForegroundColor Cyan
npx --yes wrangler deploy
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Host "[mutda-open-beta] wrangler deploy failed exit=$code" -ForegroundColor Red
    Write-Host "[mutda-open-beta] blocker: auth (wrangler login or CLOUDFLARE_API_TOKEN), zone routes mutda.ai, or DNS" -ForegroundColor Yellow
    exit $code
}

Write-Host "[mutda-open-beta] deploy harness OK · PRODUCT_DONE=false · commander ACK still required for product claim" -ForegroundColor Green
exit 0
