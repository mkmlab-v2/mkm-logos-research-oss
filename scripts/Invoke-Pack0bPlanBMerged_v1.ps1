# Pack 0-B: post-Qwen eval + Plan B resolution + optional SFT v2 convert (no train).
param(
    [int]$EvalLimit = 25,
    [switch]$SkipEval,
    [switch]$BuildSftV2,
    [switch]$SkipResolution
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    if (-not $SkipEval) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-Pack0bQwenPostTrainEval_v1.ps1 -Limit $EvalLimit
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    if (-not $SkipResolution) {
        & py scripts/apply_pack0b_plan_b_after_qwen_v1.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    if ($BuildSftV2) {
        $sftOut = "data/training/myeongri_deterministic_lora_sft_compact_qwen_train_v2.jsonl"
        & py scripts/convert_myeongri_golden_to_sft_instruction_jsonl_v1.py `
            --input-jsonl data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl `
            --output-jsonl $sftOut `
            --compact-output
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host "SFT v2 written: $sftOut"
    }
    exit 0
} finally {
    Pop-Location
}
