param(
  [string]$EvalJson = "reports/myeongri_deterministic_lora_locked_eval_inference_eval_latest.json",
  [string]$GpuStabilityJson = "reports/gpu_stability_recommended_latest.json",
  [string]$AdapterPath = "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_train_default_completion",
  [string]$PerformanceOut = "reports/generic_llm_performance_latest.json",
  [string]$StabilityOut = "reports/generic_llm_stability_latest.json",
  [string]$CostOut = "reports/generic_llm_cost_latest.json",
  [string]$GateOut = "reports/generic_llm_promotion_gate_latest.json",
  [string]$GateAnalysisOut = "reports/generic_llm_gate_analysis_latest.json",
  [string]$LlmJudgeJson = "reports/generic_llm_judge_latest.json",
  [switch]$SkipLlmJudgeShadow
)

$ErrorActionPreference = "Stop"

if (-not $SkipLlmJudgeShadow) {
  py "scripts/build_generic_llm_judge_shadow_v1.py" --eval-json $EvalJson --out $LlmJudgeJson
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

py "scripts/build_generic_llm_gate_inputs_v1.py" `
  --eval-json $EvalJson `
  --gpu-stability-json $GpuStabilityJson `
  --adapter-path $AdapterPath `
  --performance-out $PerformanceOut `
  --stability-out $StabilityOut `
  --cost-out $CostOut

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$gateArgs = @(
  "scripts/build_lora_pack_promotion_gate_v1.py",
  "--performance-json", $PerformanceOut,
  "--stability-json", $StabilityOut,
  "--cost-json", $CostOut,
  "--output", $GateOut
)
if ((-not $SkipLlmJudgeShadow) -and (Test-Path -LiteralPath $LlmJudgeJson)) {
  $gateArgs += @("--llm-judge-json", $LlmJudgeJson)
}
py @gateArgs

$gateExit = $LASTEXITCODE

py "scripts/analyze_lora_gate_report_v1.py" `
  --gate-report $GateOut `
  --out $GateAnalysisOut

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
exit $gateExit

