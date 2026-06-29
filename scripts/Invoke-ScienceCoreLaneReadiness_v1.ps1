<#
.SYNOPSIS
  Science Core B-track lane readiness (scripts + governance contract) [HYPO][research_only].

.NOTES
  Does not run full governance bundle. For weekly eval use Run-ScienceCoreGovernanceBundle_v1.ps1.
#>
[CmdletBinding()]
param(
    [switch]$StrictGovernance,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$pyArgs = @("scripts/check_science_core_lane_readiness_v1.py")
if ($StrictGovernance) { $pyArgs += "--strict-governance" }

py @pyArgs
exit $LASTEXITCODE
