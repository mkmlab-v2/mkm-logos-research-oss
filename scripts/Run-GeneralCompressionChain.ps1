<#
.SYNOPSIS
  General-rail benchmark chain: eval input -> A/B -> KPI gate -> taxonomy -> domain guard ->
  token-loss aggregate -> bundle validate -> optional B-track mirror copy ->
  optional Multilens anchor.

.PARAMETER SkipBtrackMirror
  Skip copying AB summary to reports/constitution/btrack_pilot/btrack_general_compression_ab_v1.json

.PARAMETER IncludeAnchor
  Run apply_general_compression_sweep_anchor_to_ultra_decision_v1.py (writes MULTILENS_* decision)

.PARAMETER IncludeBtrackBundle
  Run run_btrack_codebook_4d_quaternion_experiment_v1.py --general-rail (slow; refresh quaternion bench)

.PARAMETER QuatSamplesPerCell
  Passed to B-track bundle when -IncludeBtrackBundle is set (default 12 for faster-than-default runs)
#>
param(
    [switch] $SkipBtrackMirror,
    [switch] $IncludeAnchor,
    [switch] $IncludeBtrackBundle,
    [int] $QuatSamplesPerCell = 12
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Step([string]$Name, [scriptblock]$Block) {
    Write-Host "==> $Name"
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed ($Name): exit code $LASTEXITCODE"
    }
}

Invoke-Step "build_general_compression_eval_input" { py scripts/build_general_compression_eval_input.py }
Invoke-Step "general_compression_ab baseline" {
    py scripts/run_general_compression_ab.py `
        --label baseline `
        --input docs/final/artifacts/general_compression_eval_input_v1.json `
        --out docs/final/artifacts/general_compression_ab_result_summary_v1.json
}
# Treatment = general_compression_sweep_balanced_v1 best_go (B/extreme/0.2/0.18/0.5); keeps A/B + anchor aligned.
Invoke-Step "general_compression_ab treatment" {
    py scripts/run_general_compression_ab.py `
        --label treatment `
        --append `
        --strategy B `
        --intensity extreme `
        --general-max-saving-rate 0.2 `
        --sensitive-max-saving-rate 0.18 `
        --hangul-max-saving-rate 0.5 `
        --input docs/final/artifacts/general_compression_eval_input_v1.json `
        --out docs/final/artifacts/general_compression_ab_result_summary_v1.json
}
Invoke-Step "report_general_compression_kpi_gate" {
    py scripts/report_general_compression_kpi_gate.py `
        --summary docs/final/artifacts/general_compression_ab_result_summary_v1.json `
        --out docs/final/artifacts/general_compression_kpi_gate_v2.json
}

function Format-Inv([object]$v) {
    if ($null -eq $v) { return "" }
    return ([Convert]::ToDecimal($v)).ToString([System.Globalization.CultureInfo]::InvariantCulture)
}

$summary = Get-Content -Raw -Path "docs/final/artifacts/general_compression_ab_result_summary_v1.json" | ConvertFrom-Json
$b = ($summary.runs | Where-Object { $_.label -eq "baseline" } | Select-Object -First 1)
$t = ($summary.runs | Where-Object { $_.label -eq "treatment" } | Select-Object -First 1)
$csv = @(
    "run_order,label,global_token_saving_rate,avg_reconstruction_fidelity_jaccard,avg_sensitive_integrity,case_count,sensitive_violation_count,regime_switch_count",
    "1,baseline,$(Format-Inv $b.global_token_saving_rate),$(Format-Inv $b.avg_reconstruction_fidelity_jaccard),$(Format-Inv $b.avg_sensitive_integrity),$(Format-Inv $b.case_count),$(Format-Inv $b.sensitive_violation_count),$(Format-Inv $b.regime_switch_metrics.switch_count)",
    "2,treatment,$(Format-Inv $t.global_token_saving_rate),$(Format-Inv $t.avg_reconstruction_fidelity_jaccard),$(Format-Inv $t.avg_sensitive_integrity),$(Format-Inv $t.case_count),$(Format-Inv $t.sensitive_violation_count),$(Format-Inv $t.regime_switch_metrics.switch_count)"
) -join "`n"
$tsPath = "docs/final/artifacts/general_compression_ab_result_timeseries_v1.csv"
New-Item -ItemType Directory -Force -Path (Split-Path $tsPath) | Out-Null
Set-Content -Path $tsPath -Value $csv -Encoding utf8

Invoke-Step "report_general_compression_failure_taxonomy" { py scripts/report_general_compression_failure_taxonomy.py }
Invoke-Step "report_general_compression_domain_guard_gate" { py scripts/report_general_compression_domain_guard_gate.py }
Invoke-Step "report_general_compression_token_loss_aggregate" { py scripts/report_general_compression_token_loss_aggregate.py }
Invoke-Step "validate_general_compression_bundle" { py scripts/validate_general_compression_bundle.py }

if (-not $SkipBtrackMirror) {
    Invoke-Step "mirror AB to btrack_pilot" {
        Copy-Item -Force `
            docs/final/artifacts/general_compression_ab_result_summary_v1.json `
            reports/constitution/btrack_pilot/btrack_general_compression_ab_v1.json
    }
}

if ($IncludeAnchor) {
    Invoke-Step "apply_general_compression_sweep_anchor_to_ultra_decision_v1" {
        py scripts/apply_general_compression_sweep_anchor_to_ultra_decision_v1.py
    }
}

if ($IncludeBtrackBundle) {
    Invoke-Step "run_btrack_codebook_4d_quaternion_experiment_v1 (--general-rail)" {
        py scripts/run_btrack_codebook_4d_quaternion_experiment_v1.py `
            --general-rail `
            --quat-samples-per-cell $QuatSamplesPerCell
    }
}

Write-Host "OK: General compression chain completed."
