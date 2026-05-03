param(
    [int]$RunsPerPrompt = 10,
    [switch]$UseSimulatedHoldSeed,
    [switch]$StrictCoverageGate,
    [switch]$SkipParse,
    [switch]$SkipIngest,
    [switch]$SkipEvaluate
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$runScript = Join-Path $PSScriptRoot "run_vibe_prompt_matrix_shadow_v1.py"
$bootstrapSlotsScript = Join-Path $PSScriptRoot "bootstrap_athena_raw_output_slots_v1.py"
$coverageScript = Join-Path $PSScriptRoot "check_vibe_raw_output_coverage_v1.py"
$integrityScript = Join-Path $PSScriptRoot "verify_vibe_gemini_slot_integrity_v1.py"
$alertScript = Join-Path $PSScriptRoot "write_vibe_gate_alert_v1.py"
$parseScript = Join-Path $PSScriptRoot "parse_athena_outputs_to_vibe_jsonl_v1.py"
$ingestScript = Join-Path $PSScriptRoot "ingest_vibe_model_outputs_v1.py"
$evalScript = Join-Path $PSScriptRoot "evaluate_vibe_prompt_consistency_v1.py"
$modelOutputJsonl = Join-Path $root "docs/final/artifacts/vibe_runs_raw/vibe_model_outputs_latest.jsonl"
$coverageJson = Join-Path $root "docs/final/artifacts/vibe_runs_raw/vibe_raw_coverage_latest.json"

Write-Host "[vibe-chain] start" -ForegroundColor Cyan
Write-Host "[vibe-chain] root=$root"
Write-Host "[vibe-chain] runs_per_prompt=$RunsPerPrompt"

if ($UseSimulatedHoldSeed) {
    Write-Host "[vibe-chain] step=matrix(simulated HOLD)"
    py $runScript --runs-per-prompt $RunsPerPrompt --simulate-decision HOLD
} else {
    Write-Host "[vibe-chain] step=matrix(pending outputs)"
    py $runScript --runs-per-prompt $RunsPerPrompt
}

Write-Host "[vibe-chain] step=bootstrap_raw_output_slots"
py $bootstrapSlotsScript --prompt-count 4 --runs-per-prompt $RunsPerPrompt

if (-not $SkipParse) {
    Write-Host "[vibe-chain] step=parse_athena_raw_outputs"
    py $parseScript
} else {
    Write-Host "[vibe-chain] step=parse skipped"
}

Write-Host "[vibe-chain] step=raw_output_coverage_check"
if ($StrictCoverageGate) {
    py $coverageScript --fail-below-filled 0.95
} else {
    py $coverageScript
}
if ($LASTEXITCODE -ne 0) {
    $gateExit = $LASTEXITCODE
    py $alertScript --status fail --stage raw_output_coverage_check --message "Filled coverage below threshold (0.95)." --exit-code $gateExit
    throw "[vibe-chain] coverage gate failed (exit=$gateExit)"
}

Write-Host "[vibe-chain] step=gemini_slot_integrity_check"
if ($StrictCoverageGate) {
    py $integrityScript --require-runtime-header --fail-on-extra-files
} else {
    py $integrityScript
}
if ($LASTEXITCODE -ne 0) {
    $gateExit = $LASTEXITCODE
    py $alertScript --status fail --stage gemini_slot_integrity_check --message "Gemini slot integrity check failed (stub markers / missing runtime header / extra files)." --exit-code $gateExit
    throw "[vibe-chain] gemini slot integrity gate failed (exit=$gateExit)"
}

if (Test-Path $coverageJson) {
    $cov = Get-Content -Raw -LiteralPath $coverageJson | ConvertFrom-Json
    if ($cov.status -eq "ok") {
        py $alertScript --status ok --stage raw_output_coverage_check --message "Coverage gate passed." --exit-code 0
    } else {
        py $alertScript --status fail --stage raw_output_coverage_check --message "Coverage check needs attention (filled coverage below policy target)." --exit-code 0
    }
} else {
    py $alertScript --status fail --stage raw_output_coverage_check --message "Coverage report missing." --exit-code 0
}

if ((-not $SkipIngest) -and (Test-Path $modelOutputJsonl)) {
    Write-Host "[vibe-chain] step=ingest_model_outputs"
    py $ingestScript --input-jsonl $modelOutputJsonl
} elseif (-not $SkipIngest) {
    Write-Host "[vibe-chain] step=ingest skipped (model output file missing): $modelOutputJsonl" -ForegroundColor Yellow
} else {
    Write-Host "[vibe-chain] step=ingest skipped"
}

if (-not $SkipEvaluate) {
    Write-Host "[vibe-chain] step=evaluate_consistency"
    py $evalScript
} else {
    Write-Host "[vibe-chain] step=evaluate skipped"
}

Write-Host "[vibe-chain] done" -ForegroundColor Green
