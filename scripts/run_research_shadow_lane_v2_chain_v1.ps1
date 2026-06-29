# Research Shadow Lane v2 — high-dim + imagination rail
param(
    [string]$IssueId = "job_prologue_suffering",
    [string]$Query = "욥이 고난을 받은 이유",
    [string]$QueryId = "job_suffering_reason",
    [switch]$SkipRouter
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "[shadow-lane-v2] M-tier chain start"

if (-not $SkipRouter) {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_hypo_generation_chain_v1.ps1 `
        -IssueId $IssueId -Query $Query -QueryId $QueryId
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    py scripts\build_research_shadow_lane_hypothesis_tree_v1.py --query-id $QueryId
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

py scripts\build_job_prologue_symbolic_energy_slice_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts\build_logos_imagination_rail_envelope_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts\build_research_shadow_lane_v2_bundle_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[shadow-lane-v2] ok"
exit 0
