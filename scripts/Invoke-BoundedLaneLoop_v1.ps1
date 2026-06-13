#Requires -Version 5.1
<#
.SYNOPSIS
  Bounded lane loop v1 — whitelist mechanical child runners (shadow outcome only).

.DESCRIPTION
  NOT infinite Cursor chat. Does NOT enqueue todo_queue or promote Track A.
  SSOT: reports/bounded_lane_loop_v1_latest.json
  Audit: reports/bounded_lane_loop_audit.jsonl

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BoundedLaneLoop_v1.ps1 -DryRun

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BoundedLaneLoop_v1.ps1 -Pin docs\final\artifacts\fixtures\bounded_lane_pin_infra_v1.example.json
#>
param(
    [string]$Pin = "docs\final\artifacts\fixtures\bounded_lane_pin_infra_v1.example.json",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $Root

$pyArgs = @("scripts/run_bounded_lane_loop_v1.py", "--pin", $Pin)
if ($DryRun) { $pyArgs += "--dry-run" }

& py @pyArgs
exit $LASTEXITCODE
