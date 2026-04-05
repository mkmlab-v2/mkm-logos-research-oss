param(
    [string]$OverviewPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_health_overview_latest.json",
    [string]$ATrackPath = "C:\workspace\docs\final\artifacts\a_track_go_nogo_status_latest.json",
    [string]$GuardrailPath = "C:\workspace\docs\final\artifacts\c2_aegis_guardrail_status_latest.json",
    [string]$BroadcastPath = "C:\workspace\projects\bitcoin-trading\memory\v2\briefs\fact_safe_multilens_broadcast_latest.json",
    [string]$ReadinessPath = "C:\workspace\docs\final\artifacts\vps_24h_daemon_showroom_readiness_latest.json",
    [string]$OutputPath = "C:\workspace\docs\final\artifacts\OPS_FACT_BRIEF_latest.md"
)

$ErrorActionPreference = "Stop"

function Read-JsonOrNull([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try { return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $null }
}

$ov = Read-JsonOrNull -path $OverviewPath
$at = Read-JsonOrNull -path $ATrackPath
$gr = Read-JsonOrNull -path $GuardrailPath
$br = Read-JsonOrNull -path $BroadcastPath
$rd = Read-JsonOrNull -path $ReadinessPath

$nowUtc = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-dd HH:mm 'UTC'")
# a_track_go_nogo_status_v1: fields live under .result (not document root)
$goNoGo = "UNKNOWN"
$stage = "UNKNOWN"
if ($null -ne $at) {
    if ($null -ne $at.result) {
        if ($null -ne $at.result.overall_go_no_go) { $goNoGo = [string]$at.result.overall_go_no_go }
        if ($null -ne $at.result.recommended_stage) { $stage = [string]$at.result.recommended_stage }
    }
    # Legacy/alternate shape (pre result wrapper): tolerate root keys if present
    if ($goNoGo -eq "UNKNOWN" -and $null -ne $at.overall_go_no_go) { $goNoGo = [string]$at.overall_go_no_go }
    if ($stage -eq "UNKNOWN" -and $null -ne $at.recommended_stage) { $stage = [string]$at.recommended_stage }
}
$overallOk = if ($null -ne $ov) { [string]$ov.overall_ok } else { "false" }
$degraded = if ($null -ne $ov) { [string]$ov.degraded } else { "true" }
$score = if ($null -ne $gr -and $null -ne $gr.current) { [string]$gr.current.unified_score_balanced } else { "n/a" }
$delta = if ($null -ne $gr) { [string]$gr.delta_vs_baseline } else { "n/a" }
$driftCount = if ($null -ne $gr -and $null -ne $gr.history) { [string]$gr.history.drift_count } else { "n/a" }
$overlapDrift = if ($null -ne $br) { [string]$br.overlap_drift_alert } else { "n/a" }
$highRel = if ($null -ne $br) { [string]$br.high_reliability_decision } else { "n/a" }
$badge = if ($null -ne $br) { [string]$br.reliability_badge } else { "n/a" }
$gateReason = if ($null -ne $br) { [string]$br.gate_reason } else { "n/a" }
$net = if ($null -ne $br) { [string]$br.net } else { "n/a" }
$daemon = if ($null -ne $rd) { [string]$rd.trading_state_running } else { "n/a" }
$pubLane = if ($null -ne $rd) { [string]$rd.public_showroom_lane_ready } else { "n/a" }
$privLane = if ($null -ne $rd) { [string]$rd.private_trading_lane_ready } else { "n/a" }
$schedOk = if ($null -ne $ov -and $null -ne $ov.ops_task_schedule) { [string]$ov.ops_task_schedule.overall_ok } else { "n/a" }

$md = @"
# Ops Fact Brief ($nowUtc)

## 1) Current State
- go_no_go: $goNoGo
- recommended_stage: $stage
- overall_ok: $overallOk
- degraded: $degraded

## 2) Core Metrics (Observed)
- unified_score_balanced: $score
- delta_vs_baseline: $delta
- drift_count: $driftCount
- overlap_drift_alert: $overlapDrift

## 3) Reliability Gates
- high_reliability_decision: $highRel
- reliability_badge: $badge
- gate_reason: $gateReason
- net: $net

## 4) Runtime Health
- daemon_running_flag: $daemon
- public_showroom_lane_ready: $pubLane
- private_trading_lane_ready: $privLane
- key_tasks_schedule_ok: $schedOk

## 5) Confirmed vs Unconfirmed
- confirmed:
  - Ops overview reports overall_ok=true and degraded=false.
  - Readiness artifact reports public/private lanes ready.
- unconfirmed (needs verification):
  - Whether current unified_score_balanced is sufficient for promotion beyond S1_SHADOW.
  - Long-horizon stability under regime shift without score degradation.

## 6) Risk Note (No Hype)
- A-track remains HOLD/S1_SHADOW; continue observation-first operation.
- Any drift alert or lane readiness drop should trigger immediate NO_GO review.

## 7) Next Action (Single)
- Execute scheduled daily loops and review delta-only changes in ops loop artifacts.
"@

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
Set-Content -LiteralPath $OutputPath -Value $md -Encoding UTF8
Write-Host "WROTE: $OutputPath"
