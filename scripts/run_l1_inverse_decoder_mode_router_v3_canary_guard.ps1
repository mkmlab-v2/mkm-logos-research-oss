<#
.SYNOPSIS
  Run one canary monitor cycle and auto-apply rollback switch if needed.

.DESCRIPTION
  - Calls Python monitor script to refresh canary status/log.
  - If action == ROLLBACK_TO_V4, sets user env var
    L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE=1
    and emits rollback event artifact.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$StatusPath = "docs/final/artifacts/l1_inverse_decoder_mode_router_v3_canary_status_latest.json",
    [string]$RollbackEventPath = "docs/final/artifacts/l1_inverse_decoder_mode_router_v3_canary_rollback_event_latest.json",
    [string]$Phase = "phase_1",
    [int]$TrafficPct = 10,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$monitorScript = Join-Path $WorkspaceRoot "scripts\run_l1_inverse_decoder_mode_router_v3_canary_monitor.py"
if (-not (Test-Path -LiteralPath $monitorScript)) {
    throw "Monitor script not found: $monitorScript"
}

Set-Location $WorkspaceRoot
py $monitorScript --phase $Phase --traffic-pct $TrafficPct | Out-Host

$statusAbs = Join-Path $WorkspaceRoot $StatusPath
if (-not (Test-Path -LiteralPath $statusAbs)) {
    throw "Status artifact not found: $statusAbs"
}

$status = Get-Content -LiteralPath $statusAbs -Raw | ConvertFrom-Json
$action = [string]$status.decision.action
$rollbackSwitch = [string]$status.decision.rollback_switch

if ($action -ne "ROLLBACK_TO_V4") {
    Write-Host "Canary action is $action. No rollback action needed."
    exit 0
}

Write-Warning "Canary requested rollback: action=$action"
if ($DryRun) {
    Write-Host "DryRun enabled; skipping env var update."
    exit 0
}

[Environment]::SetEnvironmentVariable("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", "1", "User")

$event = [ordered]@{
    schema = "l1_inverse_decoder_mode_router_v3_canary_rollback_event_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    action = $action
    applied = $true
    applied_target = "UserEnvironmentVariable"
    env_key = "L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE"
    env_value = "1"
    rollback_switch = $rollbackSwitch
    source_status = $statusAbs
}

$eventAbs = Join-Path $WorkspaceRoot $RollbackEventPath
$eventDir = Split-Path -Parent $eventAbs
if (-not (Test-Path -LiteralPath $eventDir)) {
    New-Item -ItemType Directory -Path $eventDir -Force | Out-Null
}

$json = $event | ConvertTo-Json -Depth 6
Set-Content -LiteralPath $eventAbs -Value $json -Encoding UTF8
Write-Host "Rollback switch applied and event saved: $eventAbs"
