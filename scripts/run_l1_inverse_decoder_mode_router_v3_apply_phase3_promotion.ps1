<#
.SYNOPSIS
  Apply phase-3 promotion (100%) when D37 decision says GO_PHASE3_100PCT.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$DecisionArtifact = "docs/final/artifacts/l1_inverse_decoder_mode_router_v3_phase3_promotion_decision_v1.json",
    [string]$PromotionEventOut = "docs/final/artifacts/l1_inverse_decoder_mode_router_v3_phase3_promotion_event_latest.json",
    [int]$IntervalMinutes = 30,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$decisionAbs = Join-Path $WorkspaceRoot $DecisionArtifact
if (-not (Test-Path -LiteralPath $decisionAbs)) {
    throw "Decision artifact not found: $decisionAbs"
}
$doc = Get-Content -LiteralPath $decisionAbs -Raw | ConvertFrom-Json
$decision = [string]$doc.decision

if ($decision -ne "GO_PHASE3_100PCT") {
    Write-Host "Decision is $decision. Phase3 promotion not applied."
    exit 0
}

$register = Join-Path $WorkspaceRoot "scripts\Register-L1InverseDecoderModeRouterV3CanaryTask.ps1"
if (-not (Test-Path -LiteralPath $register)) {
    throw "Register script not found: $register"
}

if ($DryRun) {
    powershell -NoProfile -ExecutionPolicy Bypass -File $register `
        -IntervalMinutes $IntervalMinutes `
        -Phase "phase_3" `
        -TrafficPct 100 `
        -DryRun
} else {
    powershell -NoProfile -ExecutionPolicy Bypass -File $register `
        -IntervalMinutes $IntervalMinutes `
        -Phase "phase_3" `
        -TrafficPct 100
}

$event = [ordered]@{
    schema = "l1_inverse_decoder_mode_router_v3_phase3_promotion_event_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    decision_artifact = $decisionAbs
    decision = $decision
    applied = (-not $DryRun)
    target_phase = "phase_3"
    target_traffic_pct = 100
    interval_minutes = $IntervalMinutes
    register_script = $register
}

$eventAbs = Join-Path $WorkspaceRoot $PromotionEventOut
$eventDir = Split-Path -Parent $eventAbs
if (-not (Test-Path -LiteralPath $eventDir)) {
    New-Item -ItemType Directory -Path $eventDir -Force | Out-Null
}
$json = $event | ConvertTo-Json -Depth 6
Set-Content -LiteralPath $eventAbs -Value $json -Encoding UTF8
Write-Host "Phase3 promotion event written: $eventAbs"
