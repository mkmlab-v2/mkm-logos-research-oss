#Requires -Version 5.1
<#
.SYNOPSIS
  Run Verify-TradingAutomationHealth.ps1 allowing expected security drift (CENTRAL/CONSTITUTION/.env).

.DESCRIPTION
  When security_integrity_status_latest.json is RED but changed_paths are only the documented
  allowlist, Verify-TradingAutomationHealth.ps1 still fails unless -AllowExpectedSecurityDrift is set.
  Also passes -AllowPolicyLockedGoNoGo so Trinity LOCKED_MODE disk NO_GO does not fail the wrapper.
  Point scheduled "weekly health" or manual ops checks at this wrapper so KPI drift does not
  mask task/GO health without changing the strict default of Verify-TradingAutomationHealth.ps1.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-TradingAutomationHealthWithExpectedDrift.ps1
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$script = Join-Path $WorkspaceRoot "scripts\Verify-TradingAutomationHealth.ps1"
if (-not (Test-Path -LiteralPath $script)) {
    throw "Missing: $script"
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -WorkspaceRoot $WorkspaceRoot `
  -AllowExpectedSecurityDrift -AllowPolicyLockedGoNoGo
exit $LASTEXITCODE
