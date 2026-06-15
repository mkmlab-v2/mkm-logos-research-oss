#Requires -Version 5.1
<#
.SYNOPSIS
  Bounded lane loop v1 — whitelist mechanical child runners (shadow outcome only).

.DESCRIPTION
  NOT infinite Cursor chat. Does NOT enqueue todo_queue or promote Track A.
  SSOT: reports/bounded_lane_loop_v1_latest.json
  Audit: reports/bounded_lane_loop_audit.jsonl
  Cost: reports/bounded_lane_loop_cost_v1.jsonl

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BoundedLaneLoop_v1.ps1 -DryRun

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BoundedLaneLoop_v1.ps1 -Lane infra -RefreshPin -DryRun

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BoundedLaneLoop_v1.ps1 -Lane infra -MetaLayerEnvelopePath docs\final\artifacts\fixtures\mkm_meta_layer_turn_envelope_v1.example.json -DryRun
#>
param(
    [ValidateSet("ms", "oracle", "infra", "design", "ops")]
    [string]$Lane = "infra",
    [string]$Pin = "",
    [string]$MetaLayerEnvelopePath = "",
    [switch]$MetaLayerEnvelopeAppend,
    [switch]$RefreshPin,
    [switch]$RefreshA2aBriefingSample,
    [switch]$SkipPinBuild,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $Root

if ($RefreshA2aBriefingSample) {
    & py scripts/build_bounded_lane_a2a_briefing_sample_v1.py --lane $Lane
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $Pin) {
    $Pin = "docs\final\artifacts\bounded_lane_pin_${Lane}_latest.json"
}

if ($RefreshPin -or (-not $SkipPinBuild -and -not (Test-Path -LiteralPath (Join-Path $Root $Pin)))) {
    $buildArgs = @("scripts/build_bounded_lane_pin_from_resume_pack_v1.py", "--lane", $Lane)
    & py @buildArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$pyArgs = @("scripts/run_bounded_lane_loop_v1.py", "--pin", $Pin)
if ($DryRun) { $pyArgs += "--dry-run" }
if ($MetaLayerEnvelopePath) {
    $pyArgs += @("--meta-layer-envelope-path", $MetaLayerEnvelopePath)
}
if ($MetaLayerEnvelopeAppend) { $pyArgs += "--meta-layer-envelope-append" }

& py @pyArgs
exit $LASTEXITCODE
