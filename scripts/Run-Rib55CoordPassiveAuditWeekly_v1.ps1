#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly rib55 + SKU-COORD passive audit runner.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$args = @("scripts\run_rib55_coord_passive_audit_v1.py")
if ($SkipPytest) {
    $args += "--skip-pytest"
}

& py @args
exit $LASTEXITCODE
