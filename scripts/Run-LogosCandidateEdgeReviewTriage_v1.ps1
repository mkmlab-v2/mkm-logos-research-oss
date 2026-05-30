#Requires -Version 5.1
<#
.SYNOPSIS
  Logos candidate-edge review triage: queue/gates/pack + covenant subset summary.
.EXAMPLE
  pwsh -NoProfile -File scripts/Run-LogosCandidateEdgeReviewTriage_v1.ps1
#>
param([switch]$SkipQueueRefresh)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$argsList = @()
if ($SkipQueueRefresh) { $argsList += "--skip-queue-refresh" }

py scripts/run_logos_candidate_edge_review_triage_v1.py @argsList
exit $LASTEXITCODE
