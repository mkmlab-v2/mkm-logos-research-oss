<#
.SYNOPSIS
  Bounded daily autopush loop (metrics → preflight → health snapshot).

.DESCRIPTION
  Invoked by Run-BtrackControlTowerOps.ps1 -Mode autopush. Runs up to -MaxRuns iterations
  with -CooldownSeconds between iterations. Exit code **3** after completing the bounded
  loop means "campaign finished" (Run-BtrackControlTowerOps normalizes 3 → 0 for schedulers).

  -MinAccuracyDelta is reserved for future grid tuning (passed through for shell compatibility).
#>
param(
    [int]$MaxRuns = 5,
    [int]$CooldownSeconds = 60,
    [double]$MinAccuracyDelta = 0.0,
    [switch]$SkipPhase2
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { "C:\workspace" }
Set-Location -LiteralPath $workspaceRoot

if ($MaxRuns -lt 1) {
    Write-Host "[autopush] MaxRuns < 1; nothing to do." -ForegroundColor Yellow
    exit 0
}

for ($r = 1; $r -le $MaxRuns; $r++) {
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

    if ($r -lt $MaxRuns -and $CooldownSeconds -gt 0) {
        Start-Sleep -Seconds $CooldownSeconds
    }
}

# Bounded campaign complete (parent maps 3 -> 0 for task scheduler success semantics).
exit 3
