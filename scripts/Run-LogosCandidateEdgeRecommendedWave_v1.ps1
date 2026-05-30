#Requires -Version 5.1
<#
.SYNOPSIS
  Recommended Logos candidate-edge wave: triage + covenant pack + ann_lite merge + LoRA net-new batch.
.EXAMPLE
  pwsh -NoProfile -File scripts/Run-LogosCandidateEdgeRecommendedWave_v1.ps1
#>
param(
  [switch]$SkipTriage,
  [switch]$SkipAnnLiteMerge,
  [switch]$SkipOffline4dBatch,
  [int]$NetNewMax = 18
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$argsList = @("--netnew-max", "$NetNewMax")
if ($SkipTriage) { $argsList += "--skip-triage" }
if ($SkipAnnLiteMerge) { $argsList += "--skip-ann-lite-merge" }
if ($SkipOffline4dBatch) { $argsList += "--skip-offline-4d-batch" }

py scripts/run_logos_candidate_edge_recommended_wave_v1.py @argsList
exit $LASTEXITCODE
