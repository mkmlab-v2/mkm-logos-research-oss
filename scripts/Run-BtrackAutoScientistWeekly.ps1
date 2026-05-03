<#
.SYNOPSIS
  Weekly B-track Auto Scientist refresh (bench metrics → preflight → health snapshot).

.DESCRIPTION
  Invoked by Run-BtrackControlTowerOps.ps1 -Mode weekly and by the
  MKM_BTrack_AutoScientist_Weekly scheduled task. Regenerates ``btrack_quality_latest.json``,
  mirrors the sweep_reports candidate path expected by ``control_tower_latest.json``,
  refreshes preflight and automation health snapshot.

  Full hypothesis-grid Auto Scientist is out-of-repo; this wrapper keeps tasks exit-zero
  and artifacts aligned (Fact-Lock paths).
#>
param(
    [switch]$SkipPhase2,
    [switch]$DisableSignalLightRouting
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { "C:\workspace" }
Set-Location -LiteralPath $workspaceRoot

& py -u (Join-Path $workspaceRoot "scripts\collect_btrack_quality_metrics.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$sweepDir = Join-Path $workspaceRoot "reports\constitution\btrack_pilot\auto_scientist\sweep_reports"
$canonical = Join-Path $workspaceRoot "reports\constitution\btrack_pilot\btrack_quality_latest.json"
$mirrored = Join-Path $sweepDir "btrack_quality_recalibrated_v1_latest.json"
New-Item -ItemType Directory -Force -Path $sweepDir | Out-Null
Copy-Item -LiteralPath $canonical -Destination $mirrored -Force

& py -u (Join-Path $workspaceRoot "scripts\run_btrack_promotion_preflight_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py -u (Join-Path $workspaceRoot "scripts\build_btrack_automation_health_snapshot_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

exit 0
