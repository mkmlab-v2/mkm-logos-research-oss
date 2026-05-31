# Purpose: rebuild interpret SFT v4 (variant curriculum) from golden bulk.

param(
    [switch]$SkipRebuild,
    [switch]$SkipOracleAudit,
    [switch]$SkipTrain,
    [int]$TrainSteps = 100,
    [switch]$SkipEval25,
    [switch]$SkipEval100,
    [switch]$SkipNarrativeAudit
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    $goldenTrain = "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl"
    $goldenEval = "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
    $sftTrain = "data/training/myeongri_interpret_sft_v4/train.jsonl"
    $sftEval = "data/training/myeongri_interpret_sft_v4/locked_eval.jsonl"
    $adapter = "storage/adapters/myeongri_interpret_lora_v0/run_interpret_v4_variant_s100"
    $profileJson = "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json"
    $profileKey = "train_default"

    if (-not $SkipRebuild) {
        Write-Host "[v4] 1/6 rebuild SFT (insight-mode=variant)"
        & py scripts/convert_myeongri_golden_to_interpret_sft_jsonl_v1.py `
            --input-jsonl $goldenTrain --output-jsonl $sftTrain --insight-mode variant
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & py scripts/convert_myeongri_golden_to_interpret_sft_jsonl_v1.py `
            --input-jsonl $goldenEval --output-jsonl $sftEval --insight-mode variant
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & py -m pytest tests/test_convert_myeongri_interpret_sft_v1.py tests/test_audit_myeongri_interpret_narrative_diversity_v1.py -q
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if (-not $SkipOracleAudit) {
        Write-Host "[v4] 2/6 oracle SFT diversity audit (locked_eval)"
        & py scripts/audit_myeongri_interpret_sft_oracle_diversity_v1.py `
            --sft-jsonl $sftEval `
            --out-json reports/myeongri_interpret_sft_v4_oracle_diversity_locked100_latest.json
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if (-not $SkipTrain) {
        Write-Host "[v4] 3/7 train interpret LoRA v4 ($TrainSteps steps, profile $profileKey)"
        $prof = Get-Content $profileJson -Raw | ConvertFrom-Json
        $p = $prof.profiles.$profileKey
        & py scripts/train_mkm_prophecy_lora_windows_fallback_v1.py `
            --dataset-path $sftTrain `
            --model-name $p.model_id `
            --max-seq-length $($p.max_seq_length) `
            --max-steps $TrainSteps `
            --batch-size $($p.batch_size) `
            --grad-accum $($p.grad_accum) `
            --learning-rate $($p.learning_rate) `
            --lora-r $($p.lora_r) `
            --lora-alpha $($p.lora_alpha) `
            --lora-dropout $($p.lora_dropout) `
            --output-dir $adapter
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if (-not $SkipEval25) {
        Write-Host "[v4] 4/7 LoRA eval locked25 (GPU)"
        & py scripts/run_myeongri_interpret_lora_inference_eval_v1.py `
            --sft-jsonl $sftEval `
            --adapter-path $adapter `
            --profile-key $profileKey `
            --limit 25 `
            --max-new-tokens 384 `
            --report-json reports/myeongri_interpret_lora_v4_eval_locked25_latest.json `
            --predictions-jsonl reports/myeongri_interpret_lora_v4_preds_locked25_latest.jsonl
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if (-not $SkipEval100) {
        Write-Host "[v4] 5/7 LoRA eval locked100 (GPU)"
        & py scripts/run_myeongri_interpret_lora_inference_eval_v1.py `
            --sft-jsonl $sftEval `
            --adapter-path $adapter `
            --profile-key $profileKey `
            --limit 100 `
            --max-new-tokens 384 `
            --report-json reports/myeongri_interpret_lora_v4_eval_locked100_latest.json `
            --predictions-jsonl reports/myeongri_interpret_lora_v4_preds_locked100_latest.jsonl
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if (-not $SkipNarrativeAudit) {
        Write-Host "[v4] 6/7 narrative diversity audit (post-train preds)"
        & py scripts/audit_myeongri_interpret_narrative_diversity_v1.py `
            --eval-json reports/myeongri_interpret_lora_v4_eval_locked100_latest.json `
            --predictions-jsonl reports/myeongri_interpret_lora_v4_preds_locked100_latest.jsonl `
            --out-json reports/myeongri_interpret_v4_narrative_diversity_audit_locked100_latest.json
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host "[v4] 7/7 done — adapter $adapter + reports/myeongri_interpret_lora_v4_eval_*"
    exit 0
} finally {
    Pop-Location
}
