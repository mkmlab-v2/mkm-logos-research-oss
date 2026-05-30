#Requires -Version 5.1
<#
.SYNOPSIS
  Auto-loop Logos candidate-edge recommended wave until net-new saturation ([HYPO] B-track).
#>
param(
    [int]$MaxIterations = 5
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
py scripts/run_logos_candidate_edge_auto_progress_v1.py --max-iterations $MaxIterations
exit $LASTEXITCODE
