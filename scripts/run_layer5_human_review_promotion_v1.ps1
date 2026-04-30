param(
  [string]$QueueJsonl = "docs/final/artifacts/layer5_incident_review_queue_v1_latest.jsonl",
  [string]$ApprovedIdsCsv = "docs/final/artifacts/layer5_review_approved_ids_template_v1.csv",
  [string]$RejectedIdsCsv = "docs/final/artifacts/layer5_review_rejected_ids_template_v1.csv",
  [string]$GoldsetOutJsonl = "docs/final/artifacts/layer5_incident_goldset_human_v1_latest.jsonl",
  [string]$GoldsetSummaryJson = "docs/final/artifacts/layer5_incident_goldset_human_summary_latest.json",
  [string]$BenchmarkOutJson = "docs/final/artifacts/layer5_policy_gate_benchmark_latest.json",
  [int]$SampleSize = 50,
  [int]$Seed = 42,
  [switch]$AllowFallbackDraft
)

$ErrorActionPreference = "Stop"

function Invoke-Step($cmd) {
  Write-Host ">> $cmd"
  iex $cmd
}

if (Test-Path $ApprovedIdsCsv) {
  Invoke-Step "py scripts/update_layer5_review_status_v1.py --input-jsonl `"$QueueJsonl`" --output-jsonl `"$QueueJsonl`" --summary-json `"docs/final/artifacts/layer5_review_status_update_summary_latest.json`" --ids-file `"$ApprovedIdsCsv`" --set-status approved --only-draft"
}

if (Test-Path $RejectedIdsCsv) {
  Invoke-Step "py scripts/update_layer5_review_status_v1.py --input-jsonl `"$QueueJsonl`" --output-jsonl `"$QueueJsonl`" --summary-json `"docs/final/artifacts/layer5_review_status_update_summary_latest.json`" --ids-file `"$RejectedIdsCsv`" --set-status rejected --only-draft"
}

$promoteCmd = "py scripts/promote_layer5_approved_goldset_v1.py --input-jsonl `"$QueueJsonl`" --output-jsonl `"$GoldsetOutJsonl`" --summary-json `"$GoldsetSummaryJson`" --sample-size $SampleSize --seed $Seed"
if ($AllowFallbackDraft) {
  $promoteCmd += " --allow-fallback-draft"
}
Invoke-Step $promoteCmd

Invoke-Step "py scripts/benchmark_layer5_policy_gate_v1.py --input-jsonl `"$GoldsetOutJsonl`" --sample-size $SampleSize --seed $Seed --output-json `"$BenchmarkOutJson`""

Write-Host "DONE: Layer5 human review promotion + benchmark"
