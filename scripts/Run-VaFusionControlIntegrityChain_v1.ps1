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

.PARAMETER SkipWebhook
  Do not POST on audit failure (CI / local runs without secrets).

.NOTES
  On audit failure only: User env FUSION_CONTROL_INTEGRITY_AUDIT_WEBHOOK_URL, else OPS_ALARM_WEBHOOK_URL.
  If both unset, failure is stdout-only (same pattern as Check-ProphecyPanel24hAlerts.ps1).
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
    [switch]$DryRun,
    [switch]$SkipWebhook
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

function Send-FusionControlIntegrityAuditFailureWebhook {
    param([string]$RootPath)
    $webhook = $env:FUSION_CONTROL_INTEGRITY_AUDIT_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        Write-Host 'Webhook alert skipped: no FUSION_CONTROL_INTEGRITY_AUDIT_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL' -ForegroundColor DarkGray
        return
    }
    $auditPath = Join-Path $RootPath 'reports\fusion_control_integrity_audit_latest.json'
    $summary = $null
    $checks = $null
    if (Test-Path -LiteralPath $auditPath) {
        try {
            $doc = Get-Content -LiteralPath $auditPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $summary = $doc.summary
            $checks = $doc.checks
        }
        catch {
            Write-Warning "Could not parse audit JSON for webhook payload: $($_.Exception.Message)"
        }
    }
    $payload = [ordered]@{
        event = 'fusion_control_integrity_audit_failed'
        ts_utc = (Get-Date).ToUniversalTime().ToString('o')
        workspace = $RootPath
        audit_path = $auditPath
        summary = $summary
        checks = $checks
    }
    $body = $payload | ConvertTo-Json -Depth 12 -Compress
    try {
        $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $body -ContentType 'application/json; charset=utf-8' -TimeoutSec 30
        Write-Host 'Webhook alert sent: fusion_control_integrity_audit_failed' -ForegroundColor Yellow
    }
    catch {
        Write-Warning "Webhook alert failed: $($_.Exception.Message)"
    }
}

Invoke-PyArgs -PyArgs $trajArgs
Invoke-PyArgs -PyArgs $fusionArgs

Write-Host ('py ' + ($auditArgs -join ' '))
if (-not $DryRun) {
    & py @auditArgs
    $auditExit = $LASTEXITCODE
    if ($auditExit -ne 0) {
        if (-not $SkipWebhook) {
            Send-FusionControlIntegrityAuditFailureWebhook -RootPath $root
        }
        else {
            Write-Host 'SKIP: audit failure webhook suppressed (-SkipWebhook)' -ForegroundColor DarkGray
        }
        throw "fusion control integrity audit failed (exit $auditExit)."
    }
}

Write-Host 'OK: VA fusion control integrity chain finished.' -ForegroundColor Green
