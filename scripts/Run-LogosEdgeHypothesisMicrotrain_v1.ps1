# Logos edge-hypothesis local micro-train — 15-row SFT JSONL → TinyLlama LoRA smoke ([HYPO] B-track).
param(
    [ValidateSet("DryRun", "Smoke")]
    [string]$Mode = "DryRun",
    [int]$MaxSteps = 8,
    [switch]$SkipTrainEntryRefresh
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

if (-not $SkipTrainEntryRefresh) {
    Write-Host "[1/3] Refresh train-entry pack (15 rows)..." -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-LogosEdgeHypothesisLoraTrainEntry_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[1/3] Skip train-entry refresh (-SkipTrainEntryRefresh)" -ForegroundColor DarkGray
}

$pyMode = if ($Mode -eq "Smoke") { "smoke" } else { "dry_run" }
Write-Host "[2/3] Logos micro-train mode=$pyMode max_steps=$MaxSteps (local GPU, no Kaggle)..." -ForegroundColor Cyan

$microArgs = @(
    "scripts/run_logos_edge_hypothesis_microtrain_v1.py",
    "--mode", $pyMode,
    "--max-steps", "$MaxSteps"
)
& py @microArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] Report: reports/logos_edge_hypothesis_microtrain_v1_latest.json" -ForegroundColor Green
if ($Mode -eq "DryRun") {
    Write-Host "[OK] Dry-run passed. Re-run with -Mode Smoke for ~5min GPU micro-train." -ForegroundColor Green
} else {
    Write-Host "[OK] Micro-train smoke complete. Adapter under reports/logos_edge_hypothesis_microtrain_v1/" -ForegroundColor Green
}
