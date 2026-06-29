#Requires -Version 5.1
<#
.SYNOPSIS
  Monthly KOSPI Field band prophecy-only revalidate (post L4 sign) [HYPO].

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-KospiFieldBandMonthlyProphecyRevalidate_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipPanelBuild,
    [switch]$SkipPremium,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$args = @("scripts\run_kospi_field_band_monthly_prophecy_revalidate_v1.py")
if ($SkipPanelBuild) { $args += "--skip-panel-build" }
if ($SkipPremium) { $args += "--skip-premium" }
if ($DryRun) {
    Write-Host "[DryRun] py $($args -join ' ')"
    exit 0
}

& py @args
exit $LASTEXITCODE
