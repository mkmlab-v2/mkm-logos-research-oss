param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SnapshotLabel = "weekly_baseline"
)

$ErrorActionPreference = "Stop"

$py = "py"
$snapshotScript = Join-Path $WorkspaceRoot "scripts\build_logos_pure_real_evidence_snapshot_v1.py"
$driftScript = Join-Path $WorkspaceRoot "scripts\build_logos_pure_real_baseline_drift_check_v1.py"
$snapshotOut = Join-Path $WorkspaceRoot "docs\final\artifacts\logos_pure_real_evidence_snapshot_latest.json"
$driftOut = Join-Path $WorkspaceRoot "docs\final\artifacts\logos_pure_real_baseline_drift_check_latest.json"

& $py $snapshotScript --output-json $snapshotOut --snapshot-label $SnapshotLabel
if ($LASTEXITCODE -ne 0) {
  throw "build_logos_pure_real_evidence_snapshot_v1.py failed with exit code $LASTEXITCODE"
}

& $py $driftScript --snapshot-index-json $snapshotOut --output-json $driftOut
if ($LASTEXITCODE -ne 0) {
  throw "build_logos_pure_real_baseline_drift_check_v1.py failed with exit code $LASTEXITCODE"
}

Write-Output "{`"ok`":true,`"script`":`"Run-LogosPureRealWeeklySnapshot-v1.ps1`",`"snapshot_output_json`":`"$snapshotOut`",`"drift_output_json`":`"$driftOut`"}"

