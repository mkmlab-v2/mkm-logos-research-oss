#Requires -Version 5.1
<#
.SYNOPSIS
  UAC wrapper — full Unregister for broken-runner legacy scheduled tasks.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-MkmLegacySchedulerBrokenTaskPruneElevated_v1.ps1
#>
$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "Invoke-MkmLegacySchedulerBrokenTaskPrune_v1.ps1"
if (-not (Test-Path -LiteralPath $script)) {
    throw "Missing $script"
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -SelfElevate
exit $LASTEXITCODE
