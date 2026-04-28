<#
.SYNOPSIS
  One-shot refresh: emit missing governance placeholders (optional), then go/nogo + hold checklist.

.DESCRIPTION
  Does not increment the multiweek tracker. For +1 week use scripts/run_a_track_s3_weekly_evidence_rollup_v1.py or the weekly scheduled task.

.PARAMETER SkipEmitGovernance
  Do not run emit_a_track_governance_artifacts_v1.py first.

.PARAMETER WorkspaceRoot
  Repository root (default C:\workspace).
#>
param(
    [switch]$SkipEmitGovernance,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if (-not $SkipEmitGovernance) {
    & py -3 "$WorkspaceRoot\scripts\emit_a_track_governance_artifacts_v1.py"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& py -3 "$WorkspaceRoot\scripts\build_a_track_go_nogo_status.py" --out "docs/final/artifacts/a_track_go_nogo_status_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py -3 "$WorkspaceRoot\scripts\build_a_track_hold_release_checklist_v1.py" --out "docs/final/artifacts/a_track_hold_release_checklist_v1_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ATrack governance refresh done."
