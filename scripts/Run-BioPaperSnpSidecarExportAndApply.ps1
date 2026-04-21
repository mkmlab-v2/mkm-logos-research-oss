# Bio: consolidated v3 -> PMID paper SNP sidecar JSON -> apply onto cohort (no Europe PMC).
# Run from repo root. Requires explicit sample_id<->pmid mapping (constitution gate).
# Optional: -MappingCoverageMin 0.95 (strict precheck via check_bio_paper_snp_mapping_coverage_v1.py; fail exit 2).
# Shortcut: -StrictMappingCoverage95 (equivalent to -MappingCoverageMin 0.95 unless MappingCoverageMin is explicitly set).
# Fast health-only validation shortcut lives in run_workspace_automation_health.ps1: -BioSnpOnly.
# CI equivalent: .github/workflows/bio-paper-snp-sidecar-smoke.yml (pytest only).

param(
    [Parameter(Mandatory = $true)]
    [string]$SamplesCsv,
    [Parameter(Mandatory = $true)]
    [string]$MappingCsv,
    [switch]$SkipExport,
    [string]$InputCsv = "",
    [string]$OutputJson = "",
    [string]$SidecarJson = "",
    [string]$OutputCsv = "",
    [string]$OutputReport = "",
    [switch]$SkipGate,
    [double]$MappingCoverageMin = 0,
    [switch]$StrictMappingCoverage95,
    [string]$CoverageOutputJson = ""
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location -LiteralPath $root

$runner = Join-Path $root "scripts\run_bio_paper_snp_sidecar_export_and_apply_v1.py"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing: $runner"
}

$pyArgs = @(
    $runner,
    "--samples-csv", $SamplesCsv,
    "--mapping-csv", $MappingCsv
)
if ($SkipExport) { $pyArgs += "--skip-export" }
if (-not [string]::IsNullOrWhiteSpace($InputCsv)) {
    $pyArgs += "--input-csv"
    $pyArgs += $InputCsv
}
if (-not [string]::IsNullOrWhiteSpace($OutputJson)) {
    $pyArgs += "--output-json"
    $pyArgs += $OutputJson
}
if (-not [string]::IsNullOrWhiteSpace($SidecarJson)) {
    $pyArgs += "--sidecar-json"
    $pyArgs += $SidecarJson
}
if (-not [string]::IsNullOrWhiteSpace($OutputCsv)) {
    $pyArgs += "--output-csv"
    $pyArgs += $OutputCsv
}
if (-not [string]::IsNullOrWhiteSpace($OutputReport)) {
    $pyArgs += "--output-report"
    $pyArgs += $OutputReport
}
if ($SkipGate) { $pyArgs += "--skip-gate" }
if ($StrictMappingCoverage95 -and $MappingCoverageMin -le 0) {
    $MappingCoverageMin = 0.95
}
if ($MappingCoverageMin -gt 0) {
    $pyArgs += "--mapping-coverage-min"
    $pyArgs += "$MappingCoverageMin"
}
if (-not [string]::IsNullOrWhiteSpace($CoverageOutputJson)) {
    $pyArgs += "--coverage-output-json"
    $pyArgs += $CoverageOutputJson
}

Write-Host "run_bio_paper_snp_sidecar_export_and_apply_v1.py" -ForegroundColor Cyan
& py @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
