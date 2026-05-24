#Requires -Version 5.1
<#
.SYNOPSIS
  V2 lens ensemble recovery grid + optional promotion bundle on honest strict pass.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-BtrackLensV2RecoverySweep_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-BtrackLensV2RecoverySweep_v1.ps1 -RunPromotionBundleOnPass
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$NeutralBps = 0.4,
    [switch]$RunPromotionBundleOnPass,
    [switch]$NoResume
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$argsPy = @(
    "scripts/run_btrack_lens_v2_recovery_sweep_v1.py",
    "--neutral-bps", "$NeutralBps",
    "--recent-trading-days", "180"
)
if ($RunPromotionBundleOnPass) { $argsPy += "--run-promotion-bundle-on-pass" }
if ($NoResume) { $argsPy += "--no-resume" }

& py @argsPy
exit $LASTEXITCODE
