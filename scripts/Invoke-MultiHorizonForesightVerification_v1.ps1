# Invoke Multi-Horizon Foresight Verification T0 chain [HYPO]
param(
    [string]$FromPhase = "P0",
    [switch]$SkipP0,
    [switch]$SkipMyeongniSmoke,
    [switch]$SkipTruthfulqa,
    [switch]$ContinueOnFail
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$pyArgs = @(
    "scripts/run_multi_horizon_foresight_verification_chain_v1.py",
    "--from-phase", $FromPhase
)
if ($SkipP0) { $pyArgs += "--skip-p0" }
if ($SkipMyeongniSmoke) { $pyArgs += "--skip-myeongni-smoke" }
if ($SkipTruthfulqa) { $pyArgs += "--skip-truthfulqa" }
if ($ContinueOnFail) { $pyArgs += "--continue-on-fail" }

& py @pyArgs
exit $LASTEXITCODE
