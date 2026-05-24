# Harness v2: build interpret SFT JSONL + pytest (no GPU train).
param(
    [switch]$SkipTests
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    $trainOut = "data/training/myeongri_interpret_sft_v1/train.jsonl"
    $evalOut = "data/training/myeongri_interpret_sft_v1/locked_eval.jsonl"
    & py scripts/convert_myeongri_golden_to_interpret_sft_jsonl_v1.py `
        --input-jsonl data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl `
        --output-jsonl $trainOut
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py scripts/convert_myeongri_golden_to_interpret_sft_jsonl_v1.py `
        --input-jsonl data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl `
        --output-jsonl $evalOut
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (-not $SkipTests) {
        & py -m pytest tests/test_convert_myeongri_interpret_sft_v1.py tests/test_run_myeongri_harness_v2_engine_interpret_smoke_v1.py -q
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    Write-Host "Interpret SFT ready: $trainOut , $evalOut"
    Write-Host "External GPU train (optional):"
    Write-Host "  py scripts/run_pack0b_deterministic_lora_pipeline_v1.py --golden-jsonl data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl --sft-jsonl $trainOut --adapter-out storage/adapters/myeongri_interpret_lora_v0/run_qwen_interpret_v1 --compact-sft --profile train_default --run-train --train-steps 300"
    exit 0
} finally {
    Pop-Location
}
