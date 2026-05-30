#Requires -Version 5.1
<#
.SYNOPSIS
  LoRA prune spike: strict survivor re-select (non-destructive) + Track L L1 + gold eval.
#>
param(
  [int]$TopN = 200,
  [int]$MaxPerSrc = 1,
  [double]$MaxCosine = 0.998,
  [double]$MinCosine = 0.92
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

py scripts/run_logos_candidate_edge_lora_prune_spike_v1.py `
  --top-n $TopN `
  --max-per-src $MaxPerSrc `
  --max-cosine $MaxCosine `
  --min-cosine $MinCosine
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] LoRA prune spike complete (non-destructive)" -ForegroundColor Green
exit 0
