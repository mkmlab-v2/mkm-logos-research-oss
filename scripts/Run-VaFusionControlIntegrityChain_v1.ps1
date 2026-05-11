<#
.SYNOPSIS
  B-track one-click: VA EMA trajectory → cross-lens fusion stub report → fusion control integrity audit.

.DESCRIPTION
  Writes (defaults under workspace reports/):
    - reports/va_trajectory_log_latest.json
    - reports/va_cooldown_event_log_latest.json (noop or intervention event)
    - reports/cross_lens_fusion_report_latest.json
    - reports/fusion_control_integrity_audit_latest.json

  Track wall: NON_GATING, ADVISORY_ONLY, B_TRACK_RESEARCH. Exit code 1 if audit summary.all_pass is false.

.PARAMETER EnableCooldown
  Passes --enable-cooldown to the trajectory builder (extreme VA may change fusion ranking; audit must still pass if bundle is consistent).

.PARAMETER DryRun
  Prints the planned py commands only.
#>
param(
    [string]$WorkspaceRoot = 'C:\workspace',
    [string]$SessionId = 'va_fusion_chain_session_v1',
    [int]$TurnIndex = 0,
    [double]$EmaAlpha = 0.35,
    [double]$TargetValence = 0.1,
    [double]$TargetArousal = 0.25,
    [string]$CandidatesStubJson = 'tests\fixtures\cross_lens_fusion_candidates_sample_v1.json',
    [switch]$EnableCooldown,
    [switch]$WriteState,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $root

$trajArgs = @(
    'scripts\build_lens_emotion_va_trajectory_v1.py',
    '--session-id', $SessionId,
    '--turn-index', "$TurnIndex",
    '--ema-alpha', "$EmaAlpha",
    '--target-valence', "$TargetValence",
    '--target-arousal', "$TargetArousal"
)
if ($EnableCooldown) { $trajArgs += '--enable-cooldown' }
if (-not $WriteState) { $trajArgs += '--no-write-state' }

$fusionArgs = @(
    'scripts\build_cross_lens_fusion_report_v1.py',
    '--candidates-stub-json', $CandidatesStubJson
)

$auditArgs = @('scripts\build_fusion_control_integrity_audit_v1.py')

function Invoke-PyArgs {
    param([string[]]$PyArgs)
    Write-Host ('py ' + ($PyArgs -join ' '))
    if (-not $DryRun) {
        & py @PyArgs
        if ($LASTEXITCODE -ne 0) { throw "py failed (exit $LASTEXITCODE)." }
    }
}

Invoke-PyArgs -PyArgs $trajArgs
Invoke-PyArgs -PyArgs $fusionArgs
Invoke-PyArgs -PyArgs $auditArgs

Write-Host 'OK: VA fusion control integrity chain finished.' -ForegroundColor Green
