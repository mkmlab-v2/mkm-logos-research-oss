<#
.SYNOPSIS
  B-track: rebuild sasang codebook JSON from lexicon+supplement, then run 4-grid Zstd spike.

.DESCRIPTION
  1) py scripts/build_myeongri_sasang_codebook_spike_v1.py
  2) py scripts/spike_4grid_myeongri_compression_v1.py with optional corpus.

.PARAMETER CorpusPath
  Repo-relative path to JSONL or text (e.g. data/logos/manuscripts/dss_parsed_enriched.jsonl).

.PARAMETER JsonlKey
  JSONL text field (default: text for DSS enriched).

.PARAMETER Samples
  Number of benchmark samples (default 100).

.PARAMETER Synthetic
  Ignore CorpusPath; use built-in synthetic corpus only.

.NOTES
  Requires: pip install zstandard. Output: docs/final/artifacts/derived/spike_4grid_myeongri_compression_latest.json
#>
param(
    [string]$CorpusPath = "data/logos/manuscripts/dss_parsed_enriched.jsonl",
    [string]$JsonlKey = "text",
    [int]$Samples = 100,
    [switch]$Synthetic
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

$build = Join-Path $RepoRoot "scripts\build_myeongri_sasang_codebook_spike_v1.py"
$spike = Join-Path $RepoRoot "scripts\spike_4grid_myeongri_compression_v1.py"
& py $build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$spikeArgs = @($spike, "--samples", "$Samples")
if (-not $Synthetic) {
    $spikeArgs += @("--corpus-path", $CorpusPath, "--jsonl-key", $JsonlKey)
}
& py @spikeArgs
exit $LASTEXITCODE
