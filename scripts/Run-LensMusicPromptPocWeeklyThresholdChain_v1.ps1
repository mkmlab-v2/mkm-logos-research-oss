[CmdletBinding()]
param(
    [switch]$SkipDashboard
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Set-Location -LiteralPath $repoRoot

$ticketReq = $env:MKM_APPROVAL_TICKET_REQUIRED
if ($ticketReq -eq "1" -or $ticketReq -ieq "true") {
    py scripts/check_mkm_approval_ticket_preflight_v1.py --execution-tag lens_music_prompt_poc_weekly_threshold
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
py scripts/sweep_lens_music_prompt_poc_thresholds_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/apply_lens_music_prompt_poc_threshold_recommendation_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/check_lens_music_prompt_poc_threshold_recommendation_drift_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/dispatch_lens_music_prompt_poc_threshold_drift_webhook_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_lens_music_prompt_poc_threshold_policy_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipDashboard) {
    py scripts/build_mkm_trackc_ops_dashboard_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($ticketReq -eq "1" -or $ticketReq -ieq "true") {
    py scripts/bump_mkm_approval_ticket_run_count_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[lens-music-threshold-chain] completed"
exit 0
