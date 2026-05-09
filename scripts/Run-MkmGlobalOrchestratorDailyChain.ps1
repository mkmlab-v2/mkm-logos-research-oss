<#
.SYNOPSIS
  Daily chain: run MKM global orchestrator single decision.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DebugPairs
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$argsList = @("scripts\mkm_global_orchestrator_v1.py")
if ($DebugPairs) {
    $argsList += "--debug-pairs"
}

& py @argsList
exit $LASTEXITCODE
