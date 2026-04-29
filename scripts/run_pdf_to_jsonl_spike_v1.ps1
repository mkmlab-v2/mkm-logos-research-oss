# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.81, L:0.58, K:0.72, M:0.46}
# Balance: 84
# Purpose: Wrapper to run PDF->JSONL spike with portable Java fallback on Windows.
# Keywords: powershell, java, wrapper, pdf, spike

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$InputPdf,

    [string]$OutputDir = "tmp/pdf_spike_v1",
    [string]$OutputJsonl = "tmp/pdf_spike_v1/pdf_spike_rows_latest.jsonl",
    [string]$OutputReport = "reports/pdf_spike_benchmark_v1_latest.json",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$portableJavaBin = Join-Path $workspace "tmp/temurin11-jre/jdk-11.0.30+7-jre/bin"

# Accept both array input and comma-separated single argument.
$normalizedInputPdf = @()
foreach ($item in $InputPdf) {
    if ([string]::IsNullOrWhiteSpace($item)) {
        continue
    }
    foreach ($piece in ($item -split ",")) {
        $trimmed = $piece.Trim()
        if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
            $normalizedInputPdf += $trimmed
        }
    }
}
if ($normalizedInputPdf.Count -eq 0) {
    throw "InputPdf is empty after normalization."
}

if (Test-Path (Join-Path $portableJavaBin "java.exe")) {
    $env:PATH = "$portableJavaBin;$env:PATH"
}

$runner = Join-Path $workspace "scripts/run_pdf_to_jsonl_spike_v1.py"
$args = @(
    $runner
    "--input-pdf"
)
$args += $normalizedInputPdf
$args += @(
    "--output-dir", $OutputDir,
    "--output-jsonl", $OutputJsonl,
    "--output-report", $OutputReport
)
if ($DryRun) {
    $args += "--dry-run"
}

Write-Host "[pdf-spike] workspace: $workspace"
Write-Host "[pdf-spike] python: py"
Write-Host "[pdf-spike] java path prepended: $portableJavaBin"
Write-Host "[pdf-spike] running..."
py @args
