# Run clinical-style sasang evaluation on real cohort + prediction files.
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/run_sasang_clinical_eval_real.ps1

$ErrorActionPreference = "Stop"

$gt = "data/constitution/korean_cohort/gt_cohort.real.latest.jsonl"
$pred = "reports/constitution/btrack_pilot/predictions.real.latest.jsonl"
$out = "reports/constitution/btrack_pilot/sasang_clinical_eval_real_latest.json"

if (-not (Test-Path $gt)) {
    Write-Host "ERROR: missing GT file: $gt"
    Write-Host "Hint: copy gt_cohort.real.latest.template.jsonl -> gt_cohort.real.latest.jsonl and fill real labels."
    exit 2
}

if (-not (Test-Path $pred)) {
    Write-Host "ERROR: missing prediction file: $pred"
    Write-Host "Hint: copy predictions.real.latest.template.jsonl -> predictions.real.latest.jsonl and fill runtime outputs."
    exit 2
}

py scripts/evaluate_sasang_clinical_metrics.py `
  --cohort $gt `
  --predictions $pred `
  --out $out

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "OK: sasang clinical evaluation complete"
Write-Host "report: $out"
