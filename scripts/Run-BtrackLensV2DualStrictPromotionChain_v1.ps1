#Requires -Version 5.1
<#
.SYNOPSIS
  B-track V2 dual strict promotion — one-click repro (source signal ON, expanded prior OFF).

.DESCRIPTION
  Wraps scripts/run_btrack_lens_v2_dual_strict_promotion_chain_v1.py
  Default: bundle refresh + v2 per-date rebuild + 180d recommended eval (nbps 0.4).
  -RunPromotionBundle: streak 5 + evidence pack (same WF artifacts; repo bundle design).

  B-track auto_promote_ready only — not A-track / live / PM2.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-BtrackLensV2DualStrictPromotionChain_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-BtrackLensV2DualStrictPromotionChain_v1.ps1 -RunPromotionBundle
#>
param(
    [int]$RecentTradingDays = 180,
    [double]$NeutralBps = 0.4,
    [switch]$SkipBundle,
    [switch]$SkipDirectionsRebuild,
    [switch]$RunPromotionBundle,
    [int]$StreakTarget = 5
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
$argsList = @(
    '-u', (Join-Path $root 'scripts\run_btrack_lens_v2_dual_strict_promotion_chain_v1.py'),
    '--recent-trading-days', "$RecentTradingDays",
    '--neutral-bps', "$NeutralBps"
)
if ($SkipBundle) { $argsList += '--skip-bundle' }
if ($SkipDirectionsRebuild) { $argsList += '--skip-directions-rebuild' }
if ($RunPromotionBundle) {
    $argsList += '--run-promotion-bundle'
    $argsList += '--streak-target'
    $argsList += "$StreakTarget"
}
& $py @argsList
exit $LASTEXITCODE
