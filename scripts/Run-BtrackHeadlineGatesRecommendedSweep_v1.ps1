#Requires -Version 5.1
<#
.SYNOPSIS
  Headline min_confidence + score_abs_deadzone grid sweep (allowlist-gated).

.DESCRIPTION
  Wraps run_prophecy_btrack_headline_gates_recommended_chain_v1.py.
  Does not promote prophecy_hit_rate_eval_latest.json.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$ScoreJson = "",
    [string]$PerDateJson = "",
    [switch]$SkipEnsembleBuild
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $root

$pyArgs = @("scripts\run_prophecy_btrack_headline_gates_recommended_chain_v1.py")
if ($ScoreJson) {
    $pyArgs += @("--score-json", $ScoreJson)
}
if ($PerDateJson) {
    $pyArgs += @("--per-date-json", $PerDateJson)
}
if ($SkipEnsembleBuild) {
    $pyArgs += "--skip-ensemble-build"
}

& py @pyArgs
exit $LASTEXITCODE
