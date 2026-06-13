#Requires -Version 5.1

<#

.SYNOPSIS

  Open CF custom token form + print MANUAL permission checklist (Tier 3).



  IMPORTANT: permissionGroupKeys prefill maps logs+edit to ZONE Logs (CF UI bug).

  User MUST manually set Account / Logs / Edit — see checklist below.



  py scripts/sync_cloudflare_logpush_token_to_env_v1.py --token cfut_...

  py scripts/provision_turnstile_logpush_r2_bundle_v1.py --assume-bucket-exists --apply

#>

$ErrorActionPreference = "Stop"

$accountId = "646e42cf881ab43043c32430e99d9af4"

$name = [uri]::EscapeDataString("MKM-turnstile-logpush-r2-v1")



# Prefill only R2 + Turnstile (logs omitted — prefill puts Zone Logs, not Account Logs)

$permissionJson = '[{"key":"workers_r2","type":"edit"},{"key":"turnstile","type":"edit"}]'

$permEnc = [uri]::EscapeDataString($permissionJson)

$url = "https://dash.cloudflare.com/profile/api-tokens?permissionGroupKeys=$permEnc&accountId=$accountId&name=$name"



Write-Host "=== Turnstile Logpush token (MANUAL checklist) ===" -ForegroundColor Cyan

Write-Host ""

Write-Host "KNOWN CF BUG: auto-prefill for logs+edit => Zone Logs (WRONG for turnstile_events)." -ForegroundColor Red

Write-Host "Do NOT trust prefill for Logs. Add Account Logs Edit by hand." -ForegroundColor Red

Write-Host ""

Write-Host "Token name: MKM-turnstile-logpush-r2-v1" -ForegroundColor Yellow

Write-Host ""

Write-Host "Permissions (3 rows — first dropdown MUST say Account, not Zone):" -ForegroundColor Yellow

Write-Host "  1) Account  | Logs              | Edit"

Write-Host "  2) Account  | Workers R2 Storage| Edit   (may prefill)"

Write-Host "  3) Account  | Turnstile         | Edit   (may prefill)"

Write-Host ""

Write-Host "If you see Zone | Logs | Edit -> DELETE that row and re-add as Account." -ForegroundColor Red

Write-Host ""

Write-Host "Account resources: Include -> Giryun288@gmail.com's Account" -ForegroundColor Yellow

Write-Host "Zone resources:    (leave default / All zones OK)" -ForegroundColor DarkGray

Write-Host ""

Write-Host "Then: Continue -> Create -> copy cfut_... -> .env CLOUDFLARE_LOGPUSH_API_TOKEN" -ForegroundColor Yellow

Write-Host ""

Write-Host "STOP: If MKM-turnstile-logpush-r2-v1 already exists on page 2, do NOT create another." -ForegroundColor Red
Write-Host "  Roll the Turnstile+R2+Logs row OR revoke duplicates first." -ForegroundColor Red
Write-Host "  Invoke-CleanupTurnstileLogpushCfTokens_v1.ps1" -ForegroundColor DarkYellow
Write-Host ""
Write-Host "Opening partial prefill (R2+Turnstile only):" -ForegroundColor Cyan

Write-Host $url

if ($env:OS -match "Windows") { Start-Process $url }

