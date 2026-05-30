#Requires -Version 5.1
<#
.SYNOPSIS
  Post-saturation Logos candidate-edge maintenance ([HYPO] B-track).
#>
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
py scripts/run_logos_candidate_edge_post_saturation_maintenance_v1.py @args
exit $LASTEXITCODE
