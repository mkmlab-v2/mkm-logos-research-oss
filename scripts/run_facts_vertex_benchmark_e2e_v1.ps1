[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$AnswerKeyJsonl = "tests/fixtures/facts_minimal_answer_key.sample.jsonl",

    [Parameter(Mandatory = $false)]
    [string]$Model = "",

    [Parameter(Mandatory = $false)]
    [string]$OutPredictionsJsonl = "docs/final/artifacts/facts_vertex_predictions_latest.jsonl",

    [Parameter(Mandatory = $false)]
    [string]$OutEvalJson = "docs/final/artifacts/facts_minimal_eval_latest.json",

    [Parameter(Mandatory = $false)]
    [string]$OutReportJson = "docs/final/artifacts/facts_vertex_benchmark_latest.json",

    [Parameter(Mandatory = $false)]
    [int]$Limit = 0,

    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $AnswerKeyJsonl)) {
    throw "Answer key not found: $AnswerKeyJsonl"
}

$pyArgs = @(
    "scripts/run_facts_vertex_benchmark_v1.py",
    "--answer-key-jsonl", $AnswerKeyJsonl,
    "--out-predictions-jsonl", $OutPredictionsJsonl,
    "--out-eval-json", $OutEvalJson,
    "--out-report-json", $OutReportJson
)
if (-not [string]::IsNullOrWhiteSpace($Model)) {
    $pyArgs += @("--model", $Model)
}
if ($Limit -gt 0) {
    $pyArgs += @("--limit", "$Limit")
}
if ($DryRun) {
    $pyArgs += "--dry-run"
}

Write-Host "[run_facts_vertex_benchmark_v1] py $($pyArgs -join ' ')"
& py @pyArgs
if ($LASTEXITCODE -ne 0) {
    throw "run_facts_vertex_benchmark_v1.py failed with exit code $LASTEXITCODE"
}
Write-Host "[OK] Vertex FACTS benchmark E2E finished."
