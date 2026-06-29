# Nemotron train lane router — Kaggle smoke vs RunPod full [HYPO research_only]
param(
    [switch]$ExecuteLocalValidate,
    [switch]$ExecuteSequential,
    [switch]$SkipPhaseA,
    [switch]$Strict,
    [int]$PrepLimit = 32,
    [int]$DryRunLimit = 8
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$argsList = @(
    'scripts/run_kaggle_nemotron_train_lane_router_v1.py',
    '--prep-limit', "$PrepLimit",
    '--dryrun-limit', "$DryRunLimit"
)
if ($ExecuteLocalValidate) { $argsList += '--execute-local-validate' }
if ($ExecuteSequential) { $argsList += '--execute-sequential' }
if ($SkipPhaseA) { $argsList += '--skip-phase-a' }
if ($Strict) { $argsList += '--strict' }

py @argsList
exit $LASTEXITCODE
