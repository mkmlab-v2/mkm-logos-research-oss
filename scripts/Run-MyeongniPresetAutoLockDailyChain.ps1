<#
.SYNOPSIS
  Daily chain: auto decide preset -> apply preset with verification/audit.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$StressCut = 0.65,
    [string]$StressJson = ""
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$argsList = @(
    "scripts\auto_lock_myeongni_conflict_arbitration_preset_v1.py",
    "--stress-cut", "$StressCut"
)
if (-not [string]::IsNullOrWhiteSpace($StressJson)) {
    $argsList += @("--stress-json", $StressJson)
}

& py @argsList
exit $LASTEXITCODE
