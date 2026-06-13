#Requires -Version 5.1
<#
.SYNOPSIS
  Week 2 fuel layer audit — NL 1:1 mapping · lexicon lookup smoke · hub developer triangle.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-NotebookLmFuelLayerAudit_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-NotebookLmFuelLayerAudit_v1.ps1 -IncludeMcpPrereqs
#>
param(
    [switch]$IncludeMcpPrereqs,
    [switch]$StrictNotebookGroups
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $Root

$exit = 0

if ($IncludeMcpPrereqs) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_notebooklm_mcp_prereqs.ps1
    if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }
}

$mapArgs = @("scripts/check_notebooklm_lane_mapping_audit_v1.py")
if ($StrictNotebookGroups) { $mapArgs += "--strict-known-groups" }
& py @mapArgs
if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }

& py scripts/check_lexicon_lookup_smoke_v1.py
if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }

& py scripts/check_hub_developer_copy_triangle_v1.py
if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }

exit $exit
