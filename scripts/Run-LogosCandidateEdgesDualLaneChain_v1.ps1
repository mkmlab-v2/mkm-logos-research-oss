#Requires -Version 5.1
<#
.SYNOPSIS
  Dual-lane Logos candidate edges: 4D kNN + ANN-lite survivor prune + compare ([HYPO] B-track).
#>
param(
    [switch]$SkipBuild,
    [switch]$Skip4d,
    [switch]$SkipAnnLite,
    [switch]$SkipPromotionGate
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$argsList = @()
if ($SkipBuild) { $argsList += '--skip-build' }
if ($Skip4d) { $argsList += '--skip-4d' }
if ($SkipAnnLite) { $argsList += '--skip-ann-lite' }
if ($SkipPromotionGate) { $argsList += '--skip-promotion-gate' }

& py scripts/run_logos_candidate_edges_dual_lane_chain_v1.py @argsList
exit $LASTEXITCODE
