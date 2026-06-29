# Research Shadow Lane v3 — v2 + comparative theology panorama
param(
    [string]$IssueId = "job_prologue_suffering",
    [string]$Query = "욥이 고난을 받은 이유",
    [string]$QueryId = "job_suffering_reason",
    [switch]$SkipRouter
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "[shadow-lane-v3] M-tier chain start"

$v2Args = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\run_research_shadow_lane_v2_chain_v1.ps1",
    "-IssueId", $IssueId, "-Query", $Query, "-QueryId", $QueryId
)
if ($SkipRouter) { $v2Args += "-SkipRouter" }
powershell @v2Args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts\build_comparative_theology_panorama_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts\build_comparative_theology_panorama_digest_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts\build_logos_four_slot_generation_envelope_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts\build_research_shadow_lane_v3_bundle_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[shadow-lane-v3] ok"
exit 0
