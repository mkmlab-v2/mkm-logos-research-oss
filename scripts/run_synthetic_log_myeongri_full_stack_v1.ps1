#requires -version 5.1
<#
.SYNOPSIS
  One-shot: synthetic LOG_METABOLISM cohort → myeongri correlation → NL metabolism ingest + log ablation.

.DESCRIPTION
  1) py scripts/generate_log_metabolism_synthetic_cohort_v1.py --run-pipeline (default 120 rows)
  2) scripts/run_nl_metabolism_auto_chain.ps1 -LocalRawPath <synthetic cohort> -SkipStaging -SkipCopyShard [-InputSpec]

  B-track smoke only; synthetic data [HYPO]. No production gating.
#>
param(
    [string]$RepoRoot = "",
    [int]$Rows = 120,
    [int]$Seed = 42,
    [string]$InputSpec = "docs\final\artifacts\MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
    [switch]$SkipV4
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

# Prefer repo .venv_lora when present so SciPy (p-values) matches ``pip install scipy`` there.
if (-not $env:MKM_PYTHON_EXE) {
    $venvPy = Join-Path $RepoRoot ".venv_lora\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPy) {
        $env:MKM_PYTHON_EXE = $venvPy
    }
}
$PythonExe = if ($env:MKM_PYTHON_EXE -and (Test-Path -LiteralPath $env:MKM_PYTHON_EXE)) {
    $env:MKM_PYTHON_EXE
} else {
    "py"
}

$synthetic = Join-Path $RepoRoot "docs\final\artifacts\derived\log_metabolism_synthetic_cohort_v1.jsonl"

Write-Host "[full_stack_v1] (1/2) generate + correlation pipeline rows=$Rows seed=$Seed"
$g = @(
    (Join-Path $RepoRoot "scripts\generate_log_metabolism_synthetic_cohort_v1.py"),
    "--rows", "$Rows",
    "--seed", "$Seed",
    "--run-pipeline"
)
& $PythonExe @g
if ($LASTEXITCODE -ne 0) {
    throw "generate_log_metabolism_synthetic_cohort_v1.py failed (exit $LASTEXITCODE)"
}

$auto = Join-Path $RepoRoot "scripts\run_nl_metabolism_auto_chain.ps1"
$args = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $auto,
    "-LocalRawPath", $synthetic,
    "-RepoRoot", $RepoRoot,
    "-SkipStaging",
    "-SkipCopyShard"
)
if ($InputSpec) {
    $args += @("-InputSpec", $InputSpec)
}
if ($SkipV4) { $args += "-SkipV4" }

Write-Host "[full_stack_v1] (2/2) nl_metabolism_auto_chain local_raw=synthetic"
& powershell @args
if ($LASTEXITCODE -ne 0) {
    throw "run_nl_metabolism_auto_chain.ps1 failed (exit $LASTEXITCODE)"
}

Write-Host "[full_stack_v1] OK correlation -> docs/final/artifacts/log_myeongri_correlation_synthetic_latest.json"
Write-Host "[full_stack_v1] OK nl_metabolism report -> docs/final/artifacts/derived/nl_metabolism_auto_chain_latest.json"
exit 0
