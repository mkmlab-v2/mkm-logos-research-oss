[CmdletBinding()]
param(
    [switch]$SkipDashboard
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Set-Location -LiteralPath $repoRoot

py scripts/mkm_append_governance_audit_log_v1.py --mission-id lens_music_prompt_poc_threshold_governance_drills_chain --stage unmanned_execution --decision chain_started --evidence-path scripts/Run-LensMusicPromptPocThresholdGovernanceDrills_v1.ps1 --actor Run-LensMusicPromptPocThresholdGovernanceDrills_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ticketReq = $env:MKM_APPROVAL_TICKET_REQUIRED
if ($ticketReq -eq "1" -or $ticketReq -ieq "true") {
    py scripts/check_mkm_approval_ticket_preflight_v1.py --execution-tag lens_music_prompt_poc_threshold_governance_drills
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-LensMusicPromptPocThresholdDriftWebhookWatchRehearsal_v1.ps1 -RestoreAfterRun
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-LensMusicPromptPocThresholdDriftWebhookWatchRehearsal_v1.ps1 -StrictMode -RestoreAfterRun
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipDashboard) {
    py scripts/build_mkm_trackc_ops_dashboard_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($ticketReq -eq "1" -or $ticketReq -ieq "true") {
    py scripts/bump_mkm_approval_ticket_run_count_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

py scripts/mkm_append_governance_audit_log_v1.py --mission-id lens_music_prompt_poc_threshold_governance_drills_chain --stage unmanned_execution --decision chain_completed --evidence-path docs/final/artifacts/lens_music_prompt_poc_threshold_watch_rehearsal_latest.json --actor Run-LensMusicPromptPocThresholdGovernanceDrills_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[lens-music-threshold-governance-drills] completed"
exit 0
