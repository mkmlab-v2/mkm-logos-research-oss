#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot Turnstile Logpush auto-apply (recommended path).

  1) bundle --assume-bucket-exists --apply
  2) on 1004/permission fail → open pre-filled token URL + watch clipboard (cfut_)
  3) sync token → re-apply bundle → dry-run verify

  py scripts/Invoke-TurnstileLogpushAutoApply_v1.ps1 is not used; run this .ps1 from repo root.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$ClipboardWaitSec = 180
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

function Invoke-BundleApply {
    & py (Join-Path $WorkspaceRoot "scripts\provision_turnstile_logpush_r2_bundle_v1.py") --assume-bucket-exists --apply 2>&1 | Out-Host
    return $LASTEXITCODE
}

function Test-LogpushJobPresentQuiet {
    & py (Join-Path $WorkspaceRoot "scripts\provision_turnstile_logpush_job_v1.py") --dry-run 2>$null | Out-Null
    $art = Join-Path $WorkspaceRoot "docs\final\artifacts\turnstile_logpush_job_provision_v1_latest.json"
    if (-not (Test-Path -LiteralPath $art)) { return $false }
    try {
        $j = Get-Content -LiteralPath $art -Raw -Encoding UTF8 | ConvertFrom-Json
        return ($j.decision -eq "ALREADY_PRESENT")
    } catch {
        return $false
    }
}

function Test-LogpushJobPresent {
    & py (Join-Path $WorkspaceRoot "scripts\provision_turnstile_logpush_job_v1.py") --dry-run 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) { return 0 }
    if (Test-LogpushJobPresentQuiet) { return 0 }
    return $LASTEXITCODE
}

function Sync-ClipboardTokenIfPresent {
    try {
        $clip = (Get-Clipboard -Raw).Trim()
    } catch {
        return $false
    }
    if ([string]::IsNullOrWhiteSpace($clip)) { return $false }
    if ($clip -notmatch '^cfut_[A-Za-z0-9_-]+$') { return $false }
    & py (Join-Path $WorkspaceRoot "scripts\sync_cloudflare_logpush_token_to_env_v1.py") --token $clip 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { return $false }
    Write-Host "synced CLOUDFLARE_LOGPUSH_API_TOKEN from clipboard" -ForegroundColor Green
    return $true
}

Write-Host "=== Turnstile Logpush auto-apply (recommended) ===" -ForegroundColor Cyan

$ec = Invoke-BundleApply
if ($ec -eq 0) {
    $dr = Test-LogpushJobPresent
    if ($dr -eq 0) {
        Write-Host "DONE: Logpush job applied (decision=APPLIED / ALREADY_PRESENT)" -ForegroundColor Green
        exit 0
    }
}

Write-Host "Bundle apply failed — opening token form + Logpush wizard (pick one path)" -ForegroundColor Yellow
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Open-TurnstileLogpushApiTokenPrefill_v1.ps1")
Start-Sleep -Milliseconds 500
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Open-TurnstileLogpushJobWizard_v1.ps1")

Write-Host "Path A: token form → copy cfut_... (clipboard auto-detect ${ClipboardWaitSec}s)" -ForegroundColor Yellow
Write-Host "Path B: Logpush wizard → Turnstile Events → R2 mkm-turnstile-logs (no API token needed)" -ForegroundColor Yellow

$deadline = (Get-Date).AddSeconds($ClipboardWaitSec)
$synced = $false
while ((Get-Date) -lt $deadline) {
    if (Test-LogpushJobPresentQuiet) {
        Write-Host "DONE: Logpush job detected (dashboard wizard Path B)" -ForegroundColor Green
        exit 0
    }
    if (Sync-ClipboardTokenIfPresent) {
        $synced = $true
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $synced) {
    if (Test-LogpushJobPresentQuiet) {
        Write-Host "DONE: Logpush job detected (dashboard wizard Path B)" -ForegroundColor Green
        exit 0
    }
    Write-Host "No cfut_ token on clipboard within ${ClipboardWaitSec}s." -ForegroundColor Red
    Write-Host "Path B: finish Logpush wizard (Turnstile Events -> R2 mkm-turnstile-logs), then re-run this script." -ForegroundColor Yellow
    exit 2
}

$ec2 = Invoke-BundleApply
if ($ec2 -ne 0) {
    Write-Host "Re-apply failed. See docs/final/artifacts/turnstile_logpush_r2_bundle_v1_latest.json" -ForegroundColor Red
    exit $ec2
}

$dr2 = Test-LogpushJobPresent
if ($dr2 -eq 0) {
    Write-Host "DONE: Logpush job present (APPLIED or dashboard wizard)" -ForegroundColor Green
    exit 0
}

Write-Host "Re-apply failed. Token lacks Account Logs Edit OR use dashboard wizard (Path B)." -ForegroundColor Red
Write-Host "Artifact: docs/final/artifacts/turnstile_logpush_r2_bundle_v1_latest.json" -ForegroundColor DarkYellow
exit $dr2
