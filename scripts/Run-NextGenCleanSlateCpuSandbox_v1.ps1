# Next-Gen clean-slate CPU sandbox (research_only)
param(
    [switch]$Execute,
    [switch]$DryRun,
    [string]$AuxHost = "DESKTOP-AP1DC83",
    [string]$AuxIp = "180.224.2.24",
    [string]$AuxShareRoot = "Z:\",
    [switch]$SkipAuxDeploy,
    [switch]$MainOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$argsList = @("scripts/run_nextgen_clean_slate_cpu_sandbox_chain_v1.py")
if ($Execute) { $argsList += "--execute" }
elseif ($DryRun) { $argsList += "--dry-run" }
else { $argsList += "--execute" }

if ($MainOnly) {
    $argsList += "--main-only"
} else {
    if ($AuxHost) { $argsList += @("--aux-host", $AuxHost) }
    if ($AuxIp) { $argsList += @("--aux-ip", $AuxIp) }
    if ($AuxShareRoot) { $argsList += @("--aux-share-root", $AuxShareRoot) }
    if ($SkipAuxDeploy) { $argsList += "--skip-aux-deploy" }
}

Write-Host "[nextgen-cpu-sandbox] $($argsList -join ' ')"
py @argsList
exit $LASTEXITCODE
