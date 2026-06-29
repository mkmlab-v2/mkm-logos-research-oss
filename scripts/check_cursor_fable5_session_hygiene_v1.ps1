# MKM Fable 5 session hygiene probe (local, no network).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_cursor_fable5_session_hygiene_v1.ps1
# Exit 0 = informational OK; exit 1 = staged secret-risk paths detected.

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$profilePath = Join-Path $Root '.cursor\fable5-lane-profile.v1.json'
$rulePath = Join-Path $Root '.cursor\rules\mkm-fable5-data-retention-lane-v1.mdc'

Write-Host '=== MKM Fable 5 session hygiene ==='
Write-Host "profile: $(Test-Path $profilePath)"
Write-Host "rule:    $(Test-Path $rulePath)"
Write-Host ''
Write-Host 'Reminder: Fable 5 = Anthropic 30d retention (safety). Not training. Privacy Mode exception.'
Write-Host 'Daily default: Auto/Composer. Fable only for dedicated long Agent chats without secrets.'
Write-Host ''

$riskPatterns = @(
    '\.env$',
    'credentials',
    'secret',
    'dpapi',
    'private_key',
    'api_key'
)

$staged = @(git diff --cached --name-only 2>$null)
$hits = @()
foreach ($f in $staged) {
    foreach ($p in $riskPatterns) {
        if ($f -match $p) { $hits += $f; break }
    }
}

if ($hits.Count -gt 0) {
    Write-Host 'WARN: staged paths may contain secrets (review before Fable/Agent commit):' -ForegroundColor Yellow
    $hits | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host 'OK: no obvious secret-like paths staged.'
exit 0
