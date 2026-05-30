# Run-LogosCandidateEdgesOfflineKnnChain_v1.ps1 — B-track candidate edge pipeline
param(
    [switch]$SkipBuild,
    [int]$MaxVerses = 2000,
    [int]$MaxCandidates = 5000,
    [int]$SurvivorTopN = 200
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $root 'scripts\run_logos_candidate_edges_offline_knn_chain_v1.py'))) {
    $root = 'C:\workspace'
}
Set-Location $root

$argsList = @(
    'scripts/run_logos_candidate_edges_offline_knn_chain_v1.py',
    '--max-verses', "$MaxVerses",
    '--max-candidates', "$MaxCandidates",
    '--survivor-top-n', "$SurvivorTopN"
)
if ($SkipBuild) { $argsList += '--skip-build' }

py @argsList
exit $LASTEXITCODE
