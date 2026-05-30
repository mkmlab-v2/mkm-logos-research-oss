# Covenant-convergence review subset → SFT JSONL train-entry pack (stub; no auto-merge). [HYPO] B-track.
param(
    [int]$MaxItems = 15,
    [switch]$RequireApproved,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

Write-Host "[Logos LoRA train entry] ann_lite covenant-convergence filter (max $MaxItems)" -ForegroundColor Cyan

$filterArgs = @(
    "scripts/filter_logos_review_queue_covenant_convergence_v1.py",
    "--max-items", "$MaxItems"
)
if ($DryRun) {
    Write-Host "[DRY] py $($filterArgs -join ' ')" -ForegroundColor Yellow
} else {
    & py @filterArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$sftArgs = @("scripts/build_logos_edge_hypothesis_sft_jsonl_v1.py")
if ($RequireApproved) { $sftArgs += "--require-approved" }
if ($DryRun) {
    Write-Host "[DRY] py $($sftArgs -join ' ')" -ForegroundColor Yellow
    exit 0
}

& py @sftArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] logos_edge_hypothesis_sft_v1_latest.jsonl + manifest (human sign-off before train/promote)" -ForegroundColor Green
