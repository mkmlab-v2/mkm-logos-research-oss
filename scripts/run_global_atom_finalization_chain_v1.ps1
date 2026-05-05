# One-click finalization chain for submission-ready artifacts.
param(
    [switch]$UseEventSource,
    [switch]$RebuildBatchFirst,
    [switch]$RequireSotaReady
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

if ($RebuildBatchFirst) {
    Write-Host "[0/6] Rebuild full-canon batch run" -ForegroundColor Cyan
    if ($UseEventSource) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_global_atom_full_canon_batch_v1.ps1" -UseEventSource
    } else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_global_atom_full_canon_batch_v1.ps1" -UseVerseSource
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[1/6] Consolidated manifest + batch report" -ForegroundColor Cyan
& py "scripts/build_global_atom_full_canon_consolidated_manifest_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_global_atom_full_canon_batch_report_v1.py" `
    "--stages-json" "docs/final/artifacts/global_atom_full_canon/global_atom_full_canon_consolidated_manifest_latest.json" `
    "--output-json" "docs/final/artifacts/global_atom_full_canon_batch_report_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/6] Submission pack" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_global_atom_submission_pack_v1.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/6] Freeze + Go/No-Go" -ForegroundColor Cyan
& py "scripts/build_global_atom_submission_freeze_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_global_atom_submission_go_nogo_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/6] Camera-ready draft/appendix" -ForegroundColor Cyan
& py "scripts/build_global_atom_camera_ready_pack_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[5/6] Camera-ready polish" -ForegroundColor Cyan
& py "scripts/build_global_atom_camera_ready_polish_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[6/6] Final ZIP bundle" -ForegroundColor Cyan
& py "scripts/build_global_atom_submission_zip_bundle_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[7/7] SOTA baseline readiness check" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_global_atom_sota_baseline_ingest_chain_v1.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$readinessPath = Join-Path $workspaceRoot "docs/final/artifacts/global_atom_sota_baseline_readiness_latest.json"
if (Test-Path -LiteralPath $readinessPath) {
    $readyDoc = Get-Content -LiteralPath $readinessPath -Raw | ConvertFrom-Json
    $allReady = [bool]$readyDoc.all_ready
    if (-not $allReady) {
        if ($RequireSotaReady) {
            Write-Error "SOTA baseline readiness is FALSE and -RequireSotaReady was specified."
            exit 2
        } else {
            Write-Warning "SOTA baseline readiness is FALSE. Submission pack is generated, but SOTA claims remain draft-only."
        }
    }
}

Write-Host "DONE: global atom finalization chain completed." -ForegroundColor Green

