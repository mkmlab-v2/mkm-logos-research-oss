#Requires -Version 5.1
<#
.SYNOPSIS
  RQ-031 light-only operator lane routine (-SkipGovernorBundle) [HYPO].

.EXAMPLE
  pwsh -File scripts/Run-ACodeOperatorAssistLaneLightRoutine_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SessionDate = "",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "[operator-lane-light] thin routine (-SkipGovernorBundle)" -ForegroundColor Cyan
$routineArgs = @("-WorkspaceRoot", $WorkspaceRoot, "-SkipGovernorBundle")
if ($SessionDate) { $routineArgs += @("-SessionDate", $SessionDate) }
if ($Strict) { $routineArgs += "-Strict" }

& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Run-ACodeOperatorAssistLaneRoutine_v1.ps1") @routineArgs
if ($LASTEXITCODE -ne 0) { throw "operator lane light routine exit $LASTEXITCODE" }

Write-Host "[operator-lane-light] light ops profile" -ForegroundColor Cyan
& $py scripts/build_a_code_light_ops_profile_v1.py
if ($LASTEXITCODE -ne 0) { throw "light ops profile exit $LASTEXITCODE" }

Write-Host "[operator-lane-light] done" -ForegroundColor Green
exit 0
