# Run submission evidence bundle + draft + camera-ready JSON (steps 35-37 of run_aramaic_mvp_chain_v1.ps1 tail).
# Prerequisites: falsification, benchmark, significance, raw OOS readiness, public-safe artifacts must exist (unchanged).
param(
    [string]$WorkspaceRoot = "",
    [string]$EvidenceBundleOutJson = "docs/final/artifacts/two_track_submission_evidence_bundle_latest.json",
    [string]$SubmissionDraftOutJson = "docs/final/artifacts/two_track_submission_draft_latest.json",
    [string]$CameraReadyOutJson = "docs/final/artifacts/two_track_submission_camera_ready_latest.json",
    [switch]$StrictPrereqs
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
} elseif (-not [System.IO.Path]::IsPathRooted($WorkspaceRoot)) {
    $WorkspaceRoot = Join-Path (Get-Location).Path $WorkspaceRoot
}
Set-Location -LiteralPath $WorkspaceRoot

$prereqs = @(
    "docs/final/artifacts/two_track_falsification_suite_latest.json",
    "docs/final/artifacts/two_track_benchmark_comparison_latest.json",
    "docs/final/artifacts/two_track_statistical_significance_report_latest.json",
    "docs/final/artifacts/two_track_raw_oos_readiness_latest.json",
    "docs/final/artifacts/two_track_public_safe_report_latest.json"
)
$missing = @()
foreach ($rel in $prereqs) {
    $p = Join-Path $WorkspaceRoot $rel
    if (-not (Test-Path -LiteralPath $p)) {
        $missing += $rel
    }
}
if ($missing.Count -gt 0) {
    $msg = "submission pack prerequisites missing; running degraded mode from evidence bundle."
    if ($StrictPrereqs) {
        Write-Host "FAIL: submission pack requires prior chain outputs (run full Aramaic MVP chain through public-safe, or restore artifacts):" -ForegroundColor Red
        $missing | ForEach-Object { Write-Host "  $_" }
        exit 2
    }
    Write-Host "WARN: $msg" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  $_" }
}

Write-Host "[1/3] Build submission evidence bundle checklist" -ForegroundColor Cyan
& py "scripts/build_two_track_submission_evidence_bundle_v1.py" "--out" $EvidenceBundleOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Build submission draft (abstract + outline)" -ForegroundColor Cyan
& py "scripts/build_two_track_submission_draft_v1.py" "--output-json" $SubmissionDraftOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] Build camera-ready submission JSON" -ForegroundColor Cyan
& py "scripts/build_two_track_submission_camera_ready_v1.py" "--draft-json" $SubmissionDraftOutJson "--output-json" $CameraReadyOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: two-track submission pack (evidence bundle + draft + camera-ready)." -ForegroundColor Green
