# Run Logos passive drift governance chain (weekly observation band)
param(
    [switch]$Full,
    [switch]$RefreshAb
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$py = "py"
$args = @("scripts/run_logos_passive_drift_governance_chain_v1.py")
if ($Full) { $args += "--full" } else { $args += "--fast" }
if ($RefreshAb) { $args += "--refresh-ab" }

& $py @args
exit $LASTEXITCODE
