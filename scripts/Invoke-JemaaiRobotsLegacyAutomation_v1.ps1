#Requires -Version 5.1
<#
.SYNOPSIS
  Automate jemaai.cloud robots.txt Disallow /legacy/ — CF API (if scoped) then origin :80 fix + verify.
.EXAMPLE
  powershell -File scripts\Invoke-JemaaiRobotsLegacyAutomation_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$PollSeconds = 120,
    [int]$PollIntervalSec = 15
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$rehearsal = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $rehearsal "sync_required_env_to_user.ps1") | Out-Null

Write-Host "==> [1/4] deploy origin robots.txt + staging" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $rehearsal "deploy_showroom_static.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [2/4] CF bot_management API (optional scope)" -ForegroundColor Cyan
py scripts/setup_cloudflare_jemaai_robots_legacy_v1.py
$cfExit = $LASTEXITCODE

Write-Host "==> [3/5] VPS sync + nginx robots origin (:80 HTTP 200)" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-JemaaiRobotsTxtOriginVps_v1.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [4/5] wrangler worker route (OAuth; CF managed robots may still win at edge)" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-DeployJemaaiRobotsWrangler_v1.ps1")
$wranglerExit = $LASTEXITCODE

Write-Host "==> [5/5] poll live robots.txt (up to ${PollSeconds}s)" -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds($PollSeconds)
$ok = $false
while ((Get-Date) -lt $deadline) {
    py -c @"
import json, urllib.request
try:
    b = urllib.request.urlopen('https://jemaai.cloud/robots.txt', timeout=30).read().decode()
    ok = 'Disallow: /legacy/' in b
    print(json.dumps({'legacy_disallow': ok, 'managed_cf': 'Cloudflare Managed' in b, 'tail': b.strip()[-160:]}))
    raise SystemExit(0 if ok else 2)
except Exception as e:
    print(json.dumps({'error': str(e)}))
    raise SystemExit(2)
"@
    if ($LASTEXITCODE -eq 0) { $ok = $true; break }
    Start-Sleep -Seconds $PollIntervalSec
}

if (-not $ok) {
    Write-Host "WARN: live robots.txt still missing Disallow /legacy/ — nginx noindex on /legacy/ remains primary block" -ForegroundColor Yellow
    Write-Host "Report: reports/cloudflare_jemaai_robots_legacy_v1_latest.json" -ForegroundColor DarkGray
    if ($cfExit -eq 2) {
        Write-Host "CF API blocked (403): token lacks Bot Management Edit — origin :80 fix applied; CF prepend may lag." -ForegroundColor Yellow
    }
    exit 2
}

Write-Host "OK: https://jemaai.cloud/robots.txt includes Disallow: /legacy/" -ForegroundColor Green
exit 0
