# Purpose: post-eval verify for interpret v4 guard448 baseline (B-track, no GPU).

param(
    [switch]$SkipPosteval,
    [switch]$SkipVerify,
    [switch]$ReapplyCommanderIfMissing
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    $eval = "reports/myeongri_interpret_lora_v4_eval_locked100_guard448_latest.json"
    $preds = "reports/myeongri_interpret_lora_v4_preds_locked100_guard448_latest.jsonl"
    $div = "reports/myeongri_interpret_v4_diversity_audit_locked100_guard448_latest.json"
    $sample = "reports/myeongri_interpret_v4_human_review_sample_latest.json"
    $status = "reports/myeongri_interpret_harness_v3_v4_status_latest.json"

    foreach ($p in @($eval, $preds)) {
        if (-not (Test-Path $p)) {
            Write-Error "missing $p — run locked100 guard448 eval first"
        }
    }

    if (-not $SkipPosteval) {
        Write-Host "[v4-g448] 1/3 posteval bundle (preserve commander review)"
        & py scripts/build_myeongri_interpret_v4_posteval_bundle_v1.py `
            --eval-json $eval `
            --predictions-jsonl $preds `
            --diversity-json $div `
            --status-json $status
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if ($ReapplyCommanderIfMissing) {
        $doc = Get-Content $sample -Raw | ConvertFrom-Json
        if (-not $doc.commander_signed_at_utc) {
            Write-Host "[v4-g448] reapply commander human review"
            & py scripts/apply_myeongri_interpret_v4_commander_human_review_v1.py
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
    }

    if (-not $SkipVerify) {
        Write-Host "[v4-g448] 2/3 auto-verify bundle"
        & py scripts/verify_myeongri_interpret_v4_guard_bundle_v1.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host "[v4-g448] 3/3 done — baseline $eval"
    exit 0
} finally {
    Pop-Location
}
