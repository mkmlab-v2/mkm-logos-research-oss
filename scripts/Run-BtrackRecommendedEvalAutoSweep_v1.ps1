#Requires -Version 5.1
<#
.SYNOPSIS
  Run B-track recommended eval chain: default neutral_bps grid sweep + apply best row to *_latest.

.DESCRIPTION
  Wraps: py scripts/run_prophecy_btrack_recommended_eval_chain_v1.py --auto-sweep-and-apply
  Measurement / [HYPO] only; does not enable live trading or A-track promotion.

.PARAMETER WorkspaceRoot
  Repo root (default C:\workspace).

.PARAMETER AutoSweepGrid
  Optional. Passed as --auto-sweep-grid (comma-separated). Omit to use script default.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-BtrackRecommendedEvalAutoSweep_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-BtrackRecommendedEvalAutoSweep_v1.ps1 -WorkspaceRoot D:\workspace -AutoSweepGrid "2,3,4"
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$AutoSweepGrid = "",
    [switch]$AlignPromotionPushPanel
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath $WorkspaceRoot
Set-Location -LiteralPath $root

$chain = Join-Path $root "scripts\run_prophecy_btrack_recommended_eval_chain_v1.py"
if (-not (Test-Path -LiteralPath $chain)) {
    throw "Missing chain script: $chain"
}

$pyArgs = @((Join-Path $root "scripts\run_prophecy_btrack_recommended_eval_chain_v1.py"), "--auto-sweep-and-apply")
if ($AutoSweepGrid) {
    $pyArgs += "--auto-sweep-grid"
    $pyArgs += $AutoSweepGrid
}
if ($AlignPromotionPushPanel) {
    $pyArgs += "--align-promotion-push-panel"
}

& py @pyArgs
exit $LASTEXITCODE
