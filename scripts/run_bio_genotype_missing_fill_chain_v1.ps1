param(
    [string]$CohortCsv = "C:\workspace\tmp\bio_real_cohort_merged_with_sidecar_v1.csv",
    [string]$GenotypeCsv = "C:\workspace\tmp\bio_genotype_long_v1.csv",
    [switch]$SyntheticMode,
    [int]$SyntheticSeed = 20260421,
    [string]$SyntheticGenotypeCsv = "C:\workspace\tmp\bio_genotype_long_synthetic_v1.csv",
    [string]$SyntheticBuildReport = "C:\workspace\reports\bio_genotype_synthetic_build_v1_latest.json",
    [string]$MappingCoverageReport = "C:\workspace\reports\bio_paper_snp_mapping_coverage_autofill_v1.json",
    [string]$MissingTemplateCsv = "C:\workspace\tmp\bio_genotype_missing_sample_template_v1.csv",
    [string]$CoverageReport = "C:\workspace\reports\bio_genotype_cohort_coverage_v1_latest.json",
    [string]$ReadinessReport = "C:\workspace\reports\bio_dna_promotion_readiness_v1_latest.json",
    [string]$SweepReport = "C:\workspace\reports\bio_dna_promotion_threshold_sweep_v1_latest.json",
    [switch]$RunThresholdSweep,
    [switch]$StrictReadiness,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

function Run-Step([string]$Name, [string[]]$StepArgs) {
    Write-Host ("RUN[{0}] py {1}" -f $Name, ($StepArgs -join " "))
    if ($DryRun) { return }
    & py @StepArgs
    if ($LASTEXITCODE -ne 0) { throw "step_failed:$Name" }
}

if (-not (Test-Path -LiteralPath $CohortCsv)) { throw "missing_cohort_csv:$CohortCsv" }
if (-not (Test-Path -LiteralPath $GenotypeCsv)) { throw "missing_genotype_csv:$GenotypeCsv" }
if (-not (Test-Path -LiteralPath $MappingCoverageReport)) { throw "missing_mapping_coverage_report:$MappingCoverageReport" }

Run-Step "genotype_coverage_report" @(
    (Join-Path $repoRoot "scripts\report_bio_genotype_cohort_coverage_v1.py"),
    "--cohort-csv", $CohortCsv,
    "--genotype-csv", $GenotypeCsv,
    "--output-json", $CoverageReport,
    "--missing-template-csv", $MissingTemplateCsv
)

$effectiveGenotypeCsv = $GenotypeCsv
if ($SyntheticMode) {
    Run-Step "build_synthetic_genotype" @(
        (Join-Path $repoRoot "scripts\generate_bio_synthetic_genotype_from_missing_template_v1.py"),
        "--missing-template-csv", $MissingTemplateCsv,
        "--fallback-cohort-csv", $CohortCsv,
        "--output-csv", $SyntheticGenotypeCsv,
        "--output-report", $SyntheticBuildReport,
        "--seed", "$SyntheticSeed"
    )
    $effectiveGenotypeCsv = $SyntheticGenotypeCsv
}

$chainArgs = @(
    (Join-Path $repoRoot "scripts\run_bio_dna_readiness_chain_v1.py"),
    "--cohort-csv", $CohortCsv,
    "--genotype-input-csv", $effectiveGenotypeCsv,
    "--mapping-coverage-report", $MappingCoverageReport,
    "--readiness-report", $ReadinessReport,
    "--threshold-sweep-report", $SweepReport
)
if ($RunThresholdSweep) { $chainArgs += "--run-threshold-sweep" }
if ($StrictReadiness) { $chainArgs += "--strict-readiness" }
Run-Step "dna_readiness_chain" $chainArgs

Write-Host "OK: run_bio_genotype_missing_fill_chain_v1 completed."
