#Requires -Version 5.1
<#
.SYNOPSIS
  [HYPO] Fills execution-eval lane + fills×prophecy shadow join (research_only; no live/Track A).
.NOTES
  SSOT: reports/btrack_fills_prophecy_join_wide_v1_latest.csv + .meta.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [ValidateSet("union", "fills", "prophecy")]
    [string]$Spine = "union",
    [switch]$SkipEvalLane
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
$argsList = @("scripts/run_btrack_fills_prophecy_join_chain_v1.py", "--spine", $Spine)
if ($SkipEvalLane) { $argsList += "--skip-eval-lane" }
& $py @argsList
exit $LASTEXITCODE
