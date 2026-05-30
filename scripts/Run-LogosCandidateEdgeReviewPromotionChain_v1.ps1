#Requires -Version 5.1
param([switch]$SkipReviewQueue, [switch]$TryPromote)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
$argsList = @()
if ($SkipReviewQueue) { $argsList += '--skip-review-queue' }
if ($TryPromote) { $argsList += '--try-promote' }
& py scripts/run_logos_candidate_edge_review_promotion_chain_v1.py @argsList
exit $LASTEXITCODE
