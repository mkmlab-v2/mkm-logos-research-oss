#Requires -Version 5.1
<#
.SYNOPSIS
  B-track ensemble v2 lane: per-date directions + strict promotion eval (opt-in).

.DESCRIPTION
  Runs run_prophecy_btrack_recommended_eval_chain_v1.py with --ensemble-v2-lane
  (v2 directions, lens features, adaptive instrument holdout). Default neutral_bps=0.8.
  [HYPO] / research_only — not live trading or A-track auto-promotion.

.PARAMETER WorkspaceRoot
  Repo root (default C:\workspace).

.PARAMETER NeutralBps
  Single-run neutral_bps when -AutoSweep is not set (default 0.8).

.PARAMETER AutoSweep
  Run --auto-sweep-and-apply with v2 grid (0.8,2,2.5,3,4,6).

.PARAMETER RebuildDirections
  Force rebuild reports/btrack_ensemble_per_date_directions_v2_latest.json.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-BtrackEnsembleV2RecommendedEval_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-BtrackEnsembleV2RecommendedEval_v1.ps1 -AutoSweep
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$NeutralBps = 0.8,
    [switch]$AutoSweep,
    [switch]$RebuildDirections
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath $WorkspaceRoot
Set-Location -LiteralPath $root

$chain = Join-Path $root "scripts\run_prophecy_btrack_recommended_eval_chain_v1.py"
if (-not (Test-Path -LiteralPath $chain)) {
    throw "Missing chain script: $chain"
}

$pyArgs = @(
    $chain
    "--ensemble-v2-lane"
)
if ($RebuildDirections) {
    $pyArgs += "--rebuild-ensemble-v2-directions"
}
if ($AutoSweep) {
    $pyArgs += "--auto-sweep-and-apply"
} else {
    $pyArgs += "--neutral-bps"
    $pyArgs += [string]$NeutralBps
}

& py @pyArgs
exit $LASTEXITCODE
