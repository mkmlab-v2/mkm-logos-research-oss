<#
.SYNOPSIS
  Build integrated_governance_v1_latest.json when config + three KOSPI gate artifacts exist.

.DESCRIPTION
  Delegates to `scripts/invoke_build_integrated_governance_if_deps_present_v1.py` (same logic as CI).
  If any dependency is missing, exits 0 with SKIP stderr (does not fail host chains).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-BuildIntegratedGovernanceIfDepsPresent_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-BuildIntegratedGovernanceIfDepsPresent_v1.ps1 -WorkspaceRoot D:\repo -SkipDigestSchemaValidation
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipDigestSchemaValidation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
}
else {
    $WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}

$pyInvoker = Join-Path $WorkspaceRoot "scripts\invoke_build_integrated_governance_if_deps_present_v1.py"
if (-not (Test-Path -LiteralPath $pyInvoker)) {
    throw "Required script not found: $pyInvoker"
}

Set-Location -LiteralPath $WorkspaceRoot
$args = @($pyInvoker, "--workspace-root", $WorkspaceRoot)
if ($SkipDigestSchemaValidation) {
    $args += "--skip-digest-schema-validation"
}
py @args
exit $LASTEXITCODE
