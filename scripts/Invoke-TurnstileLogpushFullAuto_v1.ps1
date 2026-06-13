#Requires -Version 5.1
<#
.SYNOPSIS
  Max-automation Turnstile Logpush: clipboard poll + sync + apply (Tier 3 roll once).

  1) Open API tokens page 2 hint
  2) Poll clipboard for cfut_ (default 300s)
  3) sync -> probe -> bundle apply -> check

  Human once: Roll ONE "Account.Turnstile + R2 +1" MKM-turnstile-logpush-r2-v1 row, copy cfut_.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$ClipboardWaitSec = 300
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

function Get-CfutFromClipboard {
    try {
        $clip = (Get-Clipboard -Raw).Trim()
    } catch {
        return $null
    }
    if ([string]::IsNullOrWhiteSpace($clip)) { return $null }
    if ($clip -match '^cfut_[A-Za-z0-9_-]+$') { return $clip }
    return $null
}

Write-Host "=== Turnstile Logpush FULL AUTO (roll + copy once) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "IN CHROME (page 2):" -ForegroundColor Yellow
Write-Host "  1) Pick MKM-turnstile-logpush-r2-v1 with Account.Turnstile + R2 + +1"
Write-Host "  2) Click Roll -> copy cfut_... (Ctrl+C)"
Write-Host "  3) Do NOT create new tokens"
Write-Host ""
Write-Host "Watching clipboard ${ClipboardWaitSec}s..." -ForegroundColor Cyan

Start-Process "https://dash.cloudflare.com/profile/api-tokens"

$deadline = (Get-Date).AddSeconds($ClipboardWaitSec)
$token = $null
$seen = @{}
while ((Get-Date) -lt $deadline) {
    $candidate = Get-CfutFromClipboard
    if (-not $candidate) {
        Start-Sleep -Seconds 2
        continue
    }
    $fp = if ($candidate.Length -ge 10) { $candidate.Substring(0, 6) + "..." + $candidate.Substring($candidate.Length - 4) } else { $candidate }
    if ($seen.ContainsKey($fp)) {
        Start-Sleep -Seconds 2
        continue
    }
    $seen[$fp] = $true
    Write-Host "Clipboard cfut detected ($fp) -> probing before sync..." -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\cleanup_turnstile_logpush_cf_tokens_v1.py") --probe-token $candidate
    if ($LASTEXITCODE -eq 0) {
        $token = $candidate
        break
    }
    Write-Host "Rejected $fp (no account/logpush perms). Roll page-2 Turnstile+R2+Logs token and copy NEW cfut_." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}

if (-not $token) {
    Write-Host "TIMEOUT: no valid cfut_ on clipboard." -ForegroundColor Red
    Write-Host "Roll MKM-turnstile-logpush-r2-v1 (page 2, Turnstile+R2+Logs) and copy fresh cfut_." -ForegroundColor Yellow
    exit 2
}

Write-Host "Valid token -> syncing..." -ForegroundColor Green
& py (Join-Path $WorkspaceRoot "scripts\sync_cloudflare_logpush_token_to_env_v1.py") --token $token
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $WorkspaceRoot "scripts\check_turnstile_logpush_auto_v1.py")
$checkEc = $LASTEXITCODE

if ($checkEc -eq 0) {
    & py (Join-Path $WorkspaceRoot "scripts\provision_turnstile_logpush_r2_bundle_v1.py") --assume-bucket-exists --apply
    if ($LASTEXITCODE -eq 0) {
        Write-Host "DONE: Logpush applied." -ForegroundColor Green
        Write-Host "Manual: revoke duplicate MKM-turnstile-logpush-r2-v1 rows on page 2." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "Probe/check/apply failed (check exit=$checkEc)." -ForegroundColor Red
Write-Host "See reports/turnstile_logpush_auto_check_latest.json" -ForegroundColor DarkYellow
exit 2
