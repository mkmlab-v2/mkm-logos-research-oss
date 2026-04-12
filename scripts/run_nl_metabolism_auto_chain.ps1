#requires -version 5.1
<#
.SYNOPSIS
  Discover LOG_METABOLISM JSONL in NotebookLM (nlm) → ingest + ablation chain; else KPI JSONL fallback.

.DESCRIPTION
  1) py scripts/discover_nl_metabolism_source.py --quiet
  2) If match: run_nl_metabolism_ingest_chain.ps1 -SourceId ...
     Else: run_nl_metabolism_ingest_chain.ps1 -RawPath -FallbackMetabolismJsonl (default KPI-derived)
  3) Writes docs/final/artifacts/derived/nl_metabolism_auto_chain_latest.json

.PARAMETER FallbackMetabolismJsonl
  Used when no NL source matches (default: docs/final/artifacts/derived/log_metabolism_from_kpi_20260412_v1.jsonl).

.PARAMETER OutJsonl
  Passed through when NL match (default log_metabolism_from_nl_v1.jsonl). On fallback, written to log_metabolism_auto_fallback_v1.jsonl unless overridden.

.PARAMETER AblationOutDir
  Ablation chain output directory.

.PARAMETER SkipAblationChain
  Ingest / copy-path only (still runs discover).

.PARAMETER SkipStaging / SkipCopyShard / SkipV4 / InputSpec
  Forwarded to run_log_ablation_chain_v1.ps1 when ablation runs.
#>
param(
    [string]$RepoRoot = "",
    [string]$FallbackMetabolismJsonl = "",
    [string]$OutJsonl = "",
    [string]$OutJsonlFallback = "",
    [string]$AblationOutDir = "",
    [string]$DiscoverReport = "",
    [switch]$SkipAblationChain,
    [string]$InputSpec = "",
    [switch]$SkipStaging,
    [switch]$SkipCopyShard,
    [switch]$SkipV4
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

if (-not $FallbackMetabolismJsonl) {
    $FallbackMetabolismJsonl = "docs\final\artifacts\derived\log_metabolism_from_kpi_20260412_v1.jsonl"
}
if (-not $OutJsonl) {
    $OutJsonl = "docs\final\artifacts\derived\log_metabolism_from_nl_v1.jsonl"
}
if (-not $OutJsonlFallback) {
    $OutJsonlFallback = "docs\final\artifacts\derived\log_metabolism_auto_fallback_v1.jsonl"
}
if (-not $AblationOutDir) {
    $AblationOutDir = "docs\final\artifacts\log_ablation_chain_nl_auto_v1"
}
if (-not $DiscoverReport) {
    $DiscoverReport = "docs\final\artifacts\derived\nl_metabolism_auto_chain_latest.json"
}

$discover = Join-Path $RepoRoot "scripts\discover_nl_metabolism_source.py"
$discJson = (& py $discover --quiet)
if ($LASTEXITCODE -ne 0) {
    throw "discover_nl_metabolism_source.py failed (exit $LASTEXITCODE)"
}
$d = $discJson | ConvertFrom-Json

$chain = Join-Path $RepoRoot "scripts\run_nl_metabolism_ingest_chain.ps1"
$chainArgs = @(
    "-AblationOutDir", (Join-Path $RepoRoot $AblationOutDir)
)
if ($InputSpec) {
    $is = if ([System.IO.Path]::IsPathRooted($InputSpec)) { $InputSpec } else { Join-Path $RepoRoot $InputSpec }
    $chainArgs += @("-InputSpec", (Resolve-Path -LiteralPath $is).Path)
}
if ($SkipStaging) { $chainArgs += "-SkipStaging" }
if ($SkipCopyShard) { $chainArgs += "-SkipCopyShard" }
if ($SkipV4) { $chainArgs += "-SkipV4" }
if ($SkipAblationChain) { $chainArgs += "-SkipAblationChain" }

$mode = "fallback_kpi"
if ($d.match -and $d.match.source_id) {
    $mode = "notebooklm_source"
    $chainArgs += @(
        "-SourceId", [string]$d.match.source_id,
        "-OutJsonl", (Join-Path $RepoRoot $OutJsonl)
    )
} else {
    $fb = if ([System.IO.Path]::IsPathRooted($FallbackMetabolismJsonl)) {
        $FallbackMetabolismJsonl
    } else {
        Join-Path $RepoRoot $FallbackMetabolismJsonl
    }
    $fb = (Resolve-Path -LiteralPath $fb).Path
    $chainArgs += @(
        "-RawPath", $fb,
        "-OutJsonl", (Join-Path $RepoRoot $OutJsonlFallback)
    )
}

Write-Host "[nl_metabolism_auto] mode=$mode"
& powershell -NoProfile -ExecutionPolicy Bypass -File $chain @chainArgs
if ($LASTEXITCODE -ne 0) {
    throw "run_nl_metabolism_ingest_chain.ps1 failed (exit $LASTEXITCODE)"
}

$reportPath = if ([System.IO.Path]::IsPathRooted($DiscoverReport)) {
    $DiscoverReport
} else {
    Join-Path $RepoRoot $DiscoverReport
}
$null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reportPath)
$report = [ordered]@{
    schema        = "nl_metabolism_auto_chain_report_v1"
    mode          = $mode
    discover      = $d
    chain_args    = $chainArgs
    generated_at  = (Get-Date).ToString("o")
}
($report | ConvertTo-Json -Depth 12) | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "WROTE report: $reportPath"
exit 0
