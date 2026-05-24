#Requires -Version 5.1
<#
.SYNOPSIS
  mkmlab DNS token bootstrap: probe -> open CF dashboard -> apply secret -> DNS ensure (best effort).

.NOTES
  API cannot create tokens without parent "User API Tokens Write". Dashboard one-time zone pick required.
#>
param(
    [switch]$SkipBrowser,
    [switch]$ApplySecretIfPresent,
    [string]$OriginIp = "148.230.97.246"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "=== [1] Token/DNS probe ===" -ForegroundColor Cyan
& py (Join-Path $root "scripts\probe_mkmlab_cloudflare_dns_token_v1.py")
$probeExit = $LASTEXITCODE

if (-not $SkipBrowser) {
    Write-Host "=== [2] Open Cloudflare API tokens (logged-in browser) ===" -ForegroundColor Cyan
    Start-Process "https://dash.cloudflare.com/profile/api-tokens"
    Write-Host @"
Dashboard steps (one-time):
  1. 토큰 생성 -> first template (영역 DNS 편집)
  2. 영역 리소스: 포함 -> 특정 영역 -> mkmlab.space (or 모든 영역)
  3. 요약 계속 -> 생성 -> copy token ONCE
  4. Paste into reports/cloudflare_dns_token_create_secret_LOCAL.json (see .template.json)
"@ -ForegroundColor Yellow
}

$secret = Join-Path $root "reports\cloudflare_dns_token_create_secret_LOCAL.json"
if ($ApplySecretIfPresent -and (Test-Path -LiteralPath $secret)) {
    Write-Host "=== [3] Apply secret + sync + DNS ensure ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-ApplyCloudflareDnsTokenToEnv_v1.ps1") -OriginIp $OriginIp
    exit $LASTEXITCODE
}

Write-Host "=== [4] VPS sync + probe (DNS may still fail until token applied) ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Sync-MkmlabRedesignToVps_v1.ps1")
& py (Join-Path $root "scripts\probe_mkmlab_space_readiness_v1.py")
$worst = [Math]::Max($probeExit, $LASTEXITCODE)
Write-Host "worst_exit=$worst (0=probe ok; DNS 403 until new token applied)" -ForegroundColor $(if ($worst -eq 0) { "Green" } else { "Yellow" })
exit $worst
