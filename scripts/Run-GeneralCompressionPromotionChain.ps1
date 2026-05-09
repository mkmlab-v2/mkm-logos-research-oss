<#
.SYNOPSIS
  End-to-end general-rail promotion: holdout split -> train/holdout manifests -> train eval ->
  parameter sweep (quick by default) -> full KPI/taxonomy/bundle chain -> Multilens anchor ->
  optional holdout-only A/B snapshot.

.PARAMETER SkipSplit
  Skip split_general_compression_holdout_v1.py (reuse existing split report + JSONL under splits_v1).

.PARAMETER SkipSweep
  Skip run_general_compression_sweep.py (reuse existing general_compression_sweep_result_v1.json).

.PARAMETER FullSweep
  Use --profile full instead of quick (much slower).

.PARAMETER SkipHoldoutAb
  Skip building holdout eval input + holdout A/B summary JSON.

.PARAMETER SkipAnchor
  Skip apply_general_compression_sweep_anchor_to_ultra_decision_v1.py (default: anchor ON).

.PARAMETER SkipBtrackMirror
  Forwarded to Run-GeneralCompressionChain.ps1

.PARAMETER IncludeBtrackBundle
  Forwarded to Run-GeneralCompressionChain.ps1
#>
param(
    [switch] $SkipSplit,
    [switch] $SkipSweep,
    [switch] $FullSweep,
    [switch] $SkipHoldoutAb,
    [switch] $SkipAnchor,
    [switch] $SkipBtrackMirror,
    [switch] $IncludeBtrackBundle,
    [int] $QuatSamplesPerCell = 12
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$TrainManifest = "docs/final/artifacts/general_compression_benchmark_manifest_train_v1.json"
$HoldoutManifest = "docs/final/artifacts/general_compression_benchmark_manifest_holdout_v1.json"
$HoldoutEval = "docs/final/artifacts/general_compression_eval_input_holdout_v1.json"
$HoldoutSummary = "docs/final/artifacts/general_compression_ab_holdout_result_summary_v1.json"

function Invoke-Step([string]$Name, [scriptblock]$Block) {
    Write-Host "==> $Name"
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed ($Name): exit code $LASTEXITCODE"
    }
}

if (-not $SkipSplit) {
    Invoke-Step "split_general_compression_holdout_v1" { py scripts/split_general_compression_holdout_v1.py }
}

Invoke-Step "build_general_compression_split_manifests_v1" { py scripts/build_general_compression_split_manifests_v1.py }

Invoke-Step "build_train_eval_input" {
    py scripts/build_general_compression_eval_input.py --manifest $TrainManifest
}

if (-not $SkipSweep) {
    $prof = if ($FullSweep) { "full" } else { "quick" }
    Invoke-Step "run_general_compression_sweep ($prof)" {
        py scripts/run_general_compression_sweep.py --profile $prof --input docs/final/artifacts/general_compression_eval_input_v1.json
    }
}

$chainPath = Join-Path $PSScriptRoot "Run-GeneralCompressionChain.ps1"
$chainSplat = @{
    SkipBuildEvalInput = $true
    QuatSamplesPerCell   = $QuatSamplesPerCell
}
if (-not $SkipAnchor) {
    $chainSplat.IncludeAnchor = $true
}
if ($SkipBtrackMirror) {
    $chainSplat.SkipBtrackMirror = $true
}
if ($IncludeBtrackBundle) {
    $chainSplat.IncludeBtrackBundle = $true
}

Write-Host "==> Run-GeneralCompressionChain (splat keys: $($chainSplat.Keys -join ', '))"
& $chainPath @chainSplat

if (-not $SkipHoldoutAb) {
    Invoke-Step "build_holdout_eval_input" {
        py scripts/build_general_compression_eval_input.py --manifest $HoldoutManifest --out $HoldoutEval
    }
    Invoke-Step "holdout_ab baseline" {
        py scripts/run_general_compression_ab.py `
            --label baseline `
            --input $HoldoutEval `
            --out $HoldoutSummary
    }
    Invoke-Step "holdout_ab treatment" {
        py scripts/run_general_compression_ab.py `
            --label treatment `
            --append `
            --strategy B `
            --intensity extreme `
            --general-max-saving-rate 0.2 `
            --sensitive-max-saving-rate 0.18 `
            --hangul-max-saving-rate 0.5 `
            --input $HoldoutEval `
            --out $HoldoutSummary
    }
}

Write-Host "OK: General compression promotion chain completed."
