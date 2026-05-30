#Requires -Version 5.1
<#
.SYNOPSIS
  31k full-corpus offline 4D kNN spike (strict LoRA survivor select, non-destructive).
.EXAMPLE
  pwsh -NoProfile -File scripts/Run-LogosCandidateEdgeFullCorpusSpike_v1.ps1
#>
param(
  [int]$SurvivorTopN = 200,
  [double]$MinCosine = 0.92
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

py scripts/run_logos_candidate_edges_offline_knn_full_corpus_spike_v1.py `
  --survivor-top-n $SurvivorTopN `
  --min-cosine $MinCosine
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] full-corpus spike chain complete" -ForegroundColor Green
exit 0
