# A-path pivot: engine JSON in prompt -> interpret envelope SFT -> short LoRA -> eval.
# Does NOT run Pack 0-B deterministic/pillars-only SFT convert.
param(
    [int]$TrainSteps = 100,
    [int]$EvalLimit = 25,
    [switch]$SkipTrain,
    [switch]$SkipEval,
    [switch]$OracleEvalOnly
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    $goldenTrain = "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl"
    $goldenEval = "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
    $sftTrain = "data/training/myeongri_interpret_sft_v2/train.jsonl"
    $sftEval = "data/training/myeongri_interpret_sft_v2/locked_eval.jsonl"
    $adapter = "storage/adapters/myeongri_interpret_lora_v0/run_pivot_a_s100_20260518"
    $profileJson = "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json"

    Write-Host "[pivot-a] 0/5 engine lookup smoke (no LLM)"
    & py scripts/manseryeok_engine_lookup_v1.py --utc-instant 1992-03-12T17:00:00Z --iana-tz Asia/Seoul --out reports/manseryeok_engine_lookup_latest.json
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[pivot-a] 1/5 convert interpret SFT (engine JSON in instruction, envelope target)"
    & py scripts/convert_myeongri_golden_to_interpret_sft_jsonl_v1.py --input-jsonl $goldenTrain --output-jsonl $sftTrain
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py scripts/convert_myeongri_golden_to_interpret_sft_jsonl_v1.py --input-jsonl $goldenEval --output-jsonl $sftEval
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[pivot-a] 2/5 pytest interpret convert + harness smoke"
    & py -m pytest tests/test_convert_myeongri_interpret_sft_v1.py tests/test_run_myeongri_harness_v2_engine_interpret_smoke_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if ($OracleEvalOnly) {
        Write-Host "[pivot-a] 3/5 oracle interpret eval (no GPU train)"
        & py scripts/run_myeongri_interpret_lora_inference_eval_v1.py `
            --sft-jsonl $sftEval `
            --oracle-sft `
            --limit $EvalLimit `
            --report-json reports/myeongri_interpret_pivot_a_oracle_eval.json `
            --predictions-jsonl reports/myeongri_interpret_pivot_a_oracle_preds.jsonl
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        exit 0
    }

    if (-not $SkipTrain) {
        Write-Host "[pivot-a] 3/5 train interpret LoRA ($TrainSteps steps, profile interpret_train_v2)"
        $prof = Get-Content $profileJson -Raw | ConvertFrom-Json
        $p = $prof.profiles.interpret_train_v2
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
            --output-dir $adapter `
            --save-steps 25 `
            --save-total-limit 3
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if ($SkipEval) { exit 0 }

    Write-Host "[pivot-a] 4/5 interpret LoRA eval (envelope match, not pillar calc)"
    & py scripts/run_myeongri_interpret_lora_inference_eval_v1.py `
        --sft-jsonl $sftEval `
        --adapter-path $adapter `
        --profile-key interpret_train_v2 `
        --limit $EvalLimit `
        --max-new-tokens 384 `
        --report-json reports/myeongri_interpret_pivot_a_eval_latest.json `
        --predictions-jsonl reports/myeongri_interpret_pivot_a_preds_latest.jsonl
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
