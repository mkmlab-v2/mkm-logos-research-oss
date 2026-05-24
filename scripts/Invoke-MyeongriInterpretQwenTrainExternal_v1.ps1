# External-terminal Qwen interpret LoRA train + optional post-eval (Harness v2).
param(
    [int]$TrainSteps = 300,
    [switch]$SkipEval
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$logDir = Join-Path $root "reports"
$trainLog = Join-Path $logDir "myeongri_interpret_qwen_train_external.log"
$trainErr = Join-Path $logDir "myeongri_interpret_qwen_train_external.err.log"
$adapter = Join-Path $root "storage\adapters\myeongri_interpret_lora_v0\run_qwen_interpret_v1"
$sft = "data/training/myeongri_interpret_sft_v1/train.jsonl"
Push-Location $root
try {
    if (-not (Test-Path $sft)) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MyeongriInterpretHarnessPrep_v1.ps1 -SkipTests
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    $pyArgs = @(
        "scripts/run_pack0b_deterministic_lora_pipeline_v1.py",
        "--golden-jsonl", "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl",
        "--sft-jsonl", $sft,
        "--adapter-out", $adapter,
        "--compact-sft",
        "--profile", "train_default",
        "--run-train",
        "--train-steps", [string]$TrainSteps,
        "--train-save-steps", "10"
    )
    Write-Host "Starting external train -> $trainLog"
    $proc = Start-Process -FilePath "py" -ArgumentList $pyArgs -WorkingDirectory $root `
        -RedirectStandardOutput $trainLog -RedirectStandardError $trainErr -PassThru -WindowStyle Hidden
    Write-Host "PID=$($proc.Id) adapter=$adapter"
    if ($SkipEval) { exit 0 }
    Write-Host "After train completes, run:"
    Write-Host "  py scripts/run_myeongri_interpret_lora_inference_eval_v1.py --adapter-path $adapter --limit 25"
    Write-Host "  py scripts/run_myeongri_harness_v2_engine_interpret_smoke_v1.py --limit 5 --run-llm --adapter-path $adapter"
    exit 0
} finally {
    Pop-Location
}
