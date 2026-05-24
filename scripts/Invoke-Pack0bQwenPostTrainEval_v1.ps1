# Post-train Pack 0-B eval (external terminal; inference only).
param(
    [int]$Limit = 25,
    [switch]$FullLockedEval
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$adapter = Join-Path $root "storage\adapters\myeongri_deterministic_lora_v0\run_pack0b_qwen_compact_v1"
if (-not (Test-Path (Join-Path $adapter "adapter_config.json"))) {
    Write-Error "Adapter missing: $adapter (wait for train to finish)"
}
$args = @(
    "scripts/run_pack0b_deterministic_lora_pipeline_v1.py",
    "--golden-jsonl", "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl",
    "--adapter-out", $adapter,
    "--run-inference-eval",
    "--inference-alignment-tier", "pillars",
    "--inference-max-new-tokens", "2048",
    "--compact-instruction",
    "--inference-predictions-jsonl", "reports/myeongri_deterministic_lora_locked_eval_predictions_qwen_compact_v1.jsonl",
    "--inference-report-json", "reports/myeongri_deterministic_lora_locked_eval_inference_eval_qwen_compact_v1.json"
)
if (-not $FullLockedEval) {
    $args += @("--inference-eval-limit", [string]$Limit)
}
Push-Location $root
try {
    & py @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
