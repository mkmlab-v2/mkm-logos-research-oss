# Next-Gen automation from main (research_only). Default: main-only (no aux PC).
param(
    [switch]$MainOnly,
    [switch]$UseAux,
    [string]$AuxIp = "180.224.2.24",
    [string]$AuxHost = "DESKTOP-AP1DC83",
    [string]$ShareRoot = "Z:\nextgen_cpu_aux",
    [int]$WaitSec = 90,
    [switch]$NoFallbackLocal
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$mainOnly = $MainOnly -or -not $UseAux
$argsList = @("scripts/run_nextgen_aux_automation_chain_v1.py")
if ($mainOnly) {
    $argsList += "--main-only"
} else {
    $argsList += @(
        "--aux-ip", $AuxIp,
        "--aux-host", $AuxHost,
        "--share-root", $ShareRoot,
        "--wait-sec", "$WaitSec"
    )
    if ($NoFallbackLocal) { $argsList += "--no-fallback-local" }
}

Write-Host "[nextgen-aux-auto] $($argsList -join ' ')" -ForegroundColor Cyan
py @argsList
exit $LASTEXITCODE
