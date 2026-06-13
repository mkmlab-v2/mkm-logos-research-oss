#Requires -Version 5.1
<#
.SYNOPSIS
  Turnstile Logpush duplicate CF token cleanup helper (Tier 3 + local probe).

  py scripts/cleanup_turnstile_logpush_cf_tokens_v1.py --dry-run
#>
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

Write-Host "=== Turnstile Logpush token cleanup ===" -ForegroundColor Cyan
& py scripts/cleanup_turnstile_logpush_cf_tokens_v1.py --dry-run
$ec = $LASTEXITCODE

Write-Host ""
Write-Host "Opening API tokens page (Human Chrome)..." -ForegroundColor Cyan
Start-Process "https://dash.cloudflare.com/profile/api-tokens"
Write-Host ""
Write-Host "Manual (page 2):" -ForegroundColor Yellow
Write-Host "  1) Keep ONE MKM-turnstile-logpush-r2-v1 with Account.Turnstile + R2 + Logs (+1)"
Write-Host "  2) Roll that token -> copy cfut_..."
Write-Host "  3) Revoke all other MKM-turnstile-logpush-r2-v1 rows"
Write-Host "  4) py scripts/sync_cloudflare_logpush_token_to_env_v1.py --token cfut_..."
Write-Host "  5) py scripts/check_turnstile_logpush_auto_v1.py"
Write-Host ""
Write-Host "Plan: docs/final/artifacts/turnstile_logpush_token_cleanup_plan_latest.md" -ForegroundColor DarkGray

exit $ec
