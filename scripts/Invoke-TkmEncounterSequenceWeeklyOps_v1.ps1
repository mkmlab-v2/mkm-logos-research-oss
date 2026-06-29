<#
.SYNOPSIS
  Weekly ops: TKM encounter_sequence P18 chain (B-track, send_gate=HOLD).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-TkmEncounterSequenceWeeklyOps_v1.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipPytest,
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$runner = Join-Path $resolvedRoot "scripts\run_tkm_encounter_sequence_p18_chain_v1.py"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$argLine = @("scripts/run_tkm_encounter_sequence_post_p68_maintenance_chain_v1.py", "--skip-http")
if ($SkipPytest) { $argLine += "--skip-pytest" }

Push-Location $resolvedRoot
try {
    & py @argLine
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($code -ne 0) {
    throw "TKM encounter_sequence weekly ops failed exit $code"
}

Write-Output "tkm_encounter_sequence_weekly_ops: ok"
