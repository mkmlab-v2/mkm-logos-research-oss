#Requires -Version 5.1
<#
.SYNOPSIS
  Public Trust viz fit-line smoke (HTML 200 + JSON 200 + payload contract).

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ShowroomTrustVizPublicSmoke_v1.ps1
  pwsh ... -Deploy -RefreshStaging   # chain + scp + nginx snippet when JEMAAI_VPS_RELOAD_NGINX=1
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [switch]$Deploy,
    [switch]$RefreshStaging
)

$ErrorActionPreference = "Stop"
$root = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else { $WorkspaceRoot }
Set-Location -LiteralPath $root

if ($Deploy) {
    $sync = Join-Path $root "scripts\sync_showroom_to_vps.ps1"
    $arg = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $sync, "-WorkspaceRoot", $root)
    if ($RefreshStaging) { $arg += "-RefreshStaging" }
    if ($env:JEMAAI_VPS_RELOAD_NGINX -ne "1") {
        Write-Host "[trust-viz-smoke] set JEMAAI_VPS_RELOAD_NGINX=1 for nginx snippet install + reload" -ForegroundColor Yellow
    }
    & powershell @arg
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& py (Join-Path $root "scripts\check_showroom_trust_viz_public_chain_v1.py")
exit $LASTEXITCODE
