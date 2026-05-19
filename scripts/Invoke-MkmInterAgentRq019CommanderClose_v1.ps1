#Requires -Version 5.1
<#
.SYNOPSIS
  Record RQ-019 commander close (after counsel sign-off) and rebuild status/handoff artifacts.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$CounselReference = "LC-2026-05-19-RQ019-CLEARED",
    [string]$Note = "commander verbal close after LC clearance"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath $WorkspaceRoot
Set-Location -LiteralPath $root

py scripts/record_mkm_inter_agent_rq019_commander_close_v1.py `
    --counsel-reference $CounselReference `
    --note $Note
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_mkm_inter_agent_encoding_status_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_mkm_inter_agent_legal_handoff_pack_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_mkm_inter_agent_rq019_closure_readiness_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_mkm_inter_agent_post_commander_approval_bundle_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] RQ-019 commander close chain OK" -ForegroundColor Green
