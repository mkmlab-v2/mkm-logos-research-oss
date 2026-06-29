#Requires -Version 5.1
<#
.SYNOPSIS
  RQ-028/029 sign-off archive pack + smoke + pointer checks ([HYPO] · no RQ CLOSED).

.EXAMPLE
  pwsh -File scripts/Run-ACodeGovernorSignoffArchiveBundle_v1.ps1
  pwsh -File scripts/Run-ACodeGovernorSignoffArchiveBundle_v1.ps1 -SkipSmoke
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipSmoke,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "[archive] operator lane refresh (thin)" -ForegroundColor Cyan
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Run-ACodeOperatorAssistLaneRoutine_v1.ps1") `
    -WorkspaceRoot $WorkspaceRoot -SkipGovernorBundle
if ($LASTEXITCODE -ne 0) { throw "operator lane routine exit $LASTEXITCODE" }

Write-Host "[archive] constitution pointer row check" -ForegroundColor Cyan
& $py scripts/check_a_code_constitution_pointer_row_v1.py --strict
if ($LASTEXITCODE -ne 0) { throw "pointer row check exit $LASTEXITCODE" }

Write-Host "[archive] sign-off archive pack" -ForegroundColor Cyan
$packArgs = @("scripts/build_a_code_governor_signoff_archive_pack_v1.py")
if ($Strict) { $packArgs += "--strict" }
& $py @packArgs
if ($LASTEXITCODE -ne 0) { throw "archive pack exit $LASTEXITCODE" }

if (-not $SkipSmoke) {
    Write-Host "[archive] governor smoke pytest" -ForegroundColor Cyan
    & pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-ACodeGovernorSmoke_v1.ps1") `
        -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "governor smoke exit $LASTEXITCODE" }
}

Write-Host "[archive] done" -ForegroundColor Green
exit 0
