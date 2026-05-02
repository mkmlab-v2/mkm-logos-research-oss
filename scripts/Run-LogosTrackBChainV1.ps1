#Requires -Version 5.1
<#
.SYNOPSIS
  Track B Logos one-shot: policy readiness report → deep fusion job (+ optional distill template).

.DESCRIPTION
  Runs report_logos_track_b_policy_readiness_v1.py, build_logos_vector_index_manifest_v1.py
  (deterministic pre-embedding manifest), then run_logos_track_b_deep_fusion_job_v1.py with
  --write-distill-template to docs/final/artifacts/logos_deep_research_distill_track_b_chain_v1_latest.json.
  Exit code follows the first failing step (readiness 1, manifest 2, optional ANN lite, job 3/4 distill).

.PARAMETER SkipDistill
  If set, omit --write-distill-template (job JSON only).

.PARAMETER SkipReadinessReport
  If set, do not run the readiness reporter first (still uses default readiness artifact for the job).

.PARAMETER IncludeAnnLite
  If set, run build_logos_vector_index_ann_lite_v1.py after manifest (default corpus cap 500 verses; not semantic embeddings).
#>
param(
    [switch]$SkipDistill,
    [switch]$SkipReadinessReport,
    [switch]$IncludeAnnLite
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

if (-not $SkipReadinessReport) {
    & py (Join-Path $RepoRoot 'scripts\report_logos_track_b_policy_readiness_v1.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& py (Join-Path $RepoRoot 'scripts\build_logos_vector_index_manifest_v1.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($IncludeAnnLite) {
    & py (Join-Path $RepoRoot 'scripts\build_logos_vector_index_ann_lite_v1.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$distillRel = 'docs\final\artifacts\logos_deep_research_distill_track_b_chain_v1_latest.json'
$distillPath = Join-Path $RepoRoot $distillRel
$distillDir = Split-Path -Parent $distillPath
if (-not (Test-Path $distillDir)) {
    New-Item -ItemType Directory -Path $distillDir -Force | Out-Null
}

$jobArgs = @(
    (Join-Path $RepoRoot 'scripts\run_logos_track_b_deep_fusion_job_v1.py')
)
if (-not $SkipDistill) {
    $jobArgs += '--write-distill-template', $distillPath
}

& py @jobArgs
exit $LASTEXITCODE
