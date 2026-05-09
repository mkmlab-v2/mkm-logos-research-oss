[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AnswerKeyJsonl,

    [Parameter(Mandatory = $true)]
    [string]$RawPredictionsJsonl,

    [Parameter(Mandatory = $false)]
    [string]$NormalizedPredictionsJsonl = "docs/final/artifacts/facts_minimal_predictions_normalized_latest.jsonl",

    [Parameter(Mandatory = $false)]
    [string]$OutJson = "docs/final/artifacts/facts_minimal_eval_latest.json",

    [Parameter(Mandatory = $false)]
    [string]$Preset = "google_facts",

    [Parameter(Mandatory = $false)]
    [string]$UnknownField = "",

    [Parameter(Mandatory = $false)]
    [string]$KaggleHandle = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $AnswerKeyJsonl)) {
    throw "Answer key not found: $AnswerKeyJsonl"
}
if (-not (Test-Path -LiteralPath $RawPredictionsJsonl)) {
    throw "Raw predictions not found: $RawPredictionsJsonl"
}

Write-Host "[1/2] Normalize raw predictions..."
$normalizeArgs = @(
    "scripts/normalize_facts_predictions_v1.py",
    "--raw-jsonl", $RawPredictionsJsonl,
    "--out-jsonl", $NormalizedPredictionsJsonl
)
& py @normalizeArgs
if ($LASTEXITCODE -ne 0) {
    throw "normalize_facts_predictions_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[2/2] Run FACTS minimal evaluation..."
$evalArgs = @(
    "scripts/run_facts_minimal_eval_v1.py",
    "--preset", $Preset,
    "--answer-key-jsonl", $AnswerKeyJsonl,
    "--predictions-jsonl", $NormalizedPredictionsJsonl,
    "--out-json", $OutJson
)
if (-not [string]::IsNullOrWhiteSpace($UnknownField)) {
    $evalArgs += @("--unknown-field", $UnknownField)
}
if (-not [string]::IsNullOrWhiteSpace($KaggleHandle)) {
    $evalArgs += @("--kaggle-handle", $KaggleHandle)
}
& py @evalArgs
if ($LASTEXITCODE -ne 0) {
    throw "run_facts_minimal_eval_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[OK] E2E completed."
Write-Host " - Normalized predictions: $NormalizedPredictionsJsonl"
Write-Host " - Evaluation report:     $OutJson"
