<#
.SYNOPSIS
  Run daily MKM Myeongri prompt chain (references + prompt assembly).

.DESCRIPTION
  Builds:
   - docs/final/artifacts/myeongri_ai_prompt_latest.txt
   - docs/final/artifacts/myeongri_external_reference_recommendation_latest.json

  Uses deterministic JSON input from latest independent-lens artifact by default.
  This is B-track enrichment only (no trading trigger).
#>
param(
    [string]$Profile = "daewoon",
    [string]$TopN = "5",
    [string]$Lang = "ko",
    [string]$Query = "",
    [string]$DeterministicJson = "C:\workspace\docs\final\artifacts\myeongni_independent_lens_from_chain_latest.json",
    [string]$PromptOut = "C:\workspace\docs\final\artifacts\myeongri_ai_prompt_latest.txt",
    [string]$RecommendationOut = "C:\workspace\docs\final\artifacts\myeongri_external_reference_recommendation_latest.json",
    [switch]$BuildAnswerDraft,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_myeongri_ai_prompt_chain_v1.py"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$args = @(
    $runner,
    "--profile", $Profile,
    "--top-n", $TopN,
    "--lang", $Lang,
    "--prompt-out", $PromptOut,
    "--recommendation-out", $RecommendationOut
)

if ($Query -and $Query.Trim().Length -gt 0) {
    $args += @("--query", $Query)
}

if (Test-Path -LiteralPath $DeterministicJson) {
    $args += @("--deterministic-json", $DeterministicJson)
}
else {
    # Keep chain alive for daily scheduling even if source artifact is absent.
    $args += @("--deterministic-json-inline", '{"missing_input":true}')
}

if ($DryRun) {
    Write-Host "[DryRun] py $($args -join ' ')"
    exit 0
}

Set-Location -LiteralPath $workspaceRoot
& py @args
if ($LASTEXITCODE -ne 0) {
    throw "run_myeongri_ai_prompt_chain_v1.py failed (exit $LASTEXITCODE)"
}

if ($BuildAnswerDraft) {
    $draftBuilder = Join-Path $workspaceRoot "scripts\build_myeongri_answer_draft_v1.py"
    if (-not (Test-Path -LiteralPath $draftBuilder)) {
        throw "Draft builder not found: $draftBuilder"
    }
    & py $draftBuilder --profile $Profile --lang $Lang --recommendation $RecommendationOut --deterministic-json $DeterministicJson
    if ($LASTEXITCODE -ne 0) {
        throw "build_myeongri_answer_draft_v1.py failed (exit $LASTEXITCODE)"
    }
}

Write-Host "Myeongri prompt chain completed."
Write-Host "PromptOut: $PromptOut"
Write-Host "RecommendationOut: $RecommendationOut"
exit 0
