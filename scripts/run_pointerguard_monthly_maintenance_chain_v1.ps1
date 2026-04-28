<#
.SYNOPSIS
  Run monthly PointerGuard maintenance chain in sequence.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

$steps = @(
    "scripts\run_pointerguard_p0_alert_drill_v1.py",
    "scripts\build_pointerguard_manual_approval_audit_report_v1.py",
    "scripts\build_pointerguard_readiness_failure_topn_v1.py",
    "scripts\build_pointerguard_monthly_maintenance_report_v1.py"
)

foreach ($step in $steps) {
    $path = Join-Path $WorkspaceRoot $step
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing step: $path"
    }
    & py $path
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed ($LASTEXITCODE): $step"
    }
}

Write-Host "Monthly maintenance chain completed."
