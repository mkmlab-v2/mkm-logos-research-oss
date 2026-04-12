#requires -version 5.1
<#
.SYNOPSIS
  Fetch NotebookLM source (nlm) → ingest LOG_METABOLISM JSONL → optional log ablation chain.

.DESCRIPTION
  1) Optional: nlm source content SOURCE_ID (writes temp; ingest reads it) OR use -RawPath.
  2) py scripts/ingest_notebooklm_metabolism_jsonl.py --out <jsonl>
  3) Unless -SkipAblationChain: scripts/run_log_ablation_chain_v1.ps1 -MetabolismJsonl <out>

.PARAMETER SourceId
  NotebookLM source UUID (mutually exclusive with RawPath).

.PARAMETER RawPath
  Local file already exported (chat paste, nlm -o file, etc.).

.PARAMETER OutJsonl
  Output JSONL (default: docs/final/artifacts/derived/log_metabolism_from_nl_v1.jsonl).

.PARAMETER AblationOutDir
  Passed to run_log_ablation_chain_v1.ps1 -OutDir (default: docs/final/artifacts/log_ablation_chain_nl_metabolism_v1).

.PARAMETER SkipAblationChain
  Ingest only.

.PARAMETER NlmBin
  nlm executable (default: nlm).
#>
param(
    [string]$RepoRoot = "",
    [string]$SourceId = "",
    [string]$RawPath = "",
    [string]$OutJsonl = "",
    [string]$AblationOutDir = "",
    [string]$IngestReport = "",
    [switch]$SkipAblationChain,
    [string]$NlmBin = "nlm",
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

$PythonExe = "py"
if ($env:MKM_PYTHON_EXE -and (Test-Path -LiteralPath $env:MKM_PYTHON_EXE)) {
    $PythonExe = $env:MKM_PYTHON_EXE
}

if (($SourceId -and $RawPath) -or (-not $SourceId -and -not $RawPath)) {
    throw "Provide exactly one of -SourceId or -RawPath"
}

if (-not $OutJsonl) {
    $OutJsonl = Join-Path $RepoRoot "docs\final\artifacts\derived\log_metabolism_from_nl_v1.jsonl"
} elseif (-not [System.IO.Path]::IsPathRooted($OutJsonl)) {
    $OutJsonl = Join-Path $RepoRoot $OutJsonl
}

$ingest = Join-Path $RepoRoot "scripts\ingest_notebooklm_metabolism_jsonl.py"
$pyArgs = @($ingest, "--out", $OutJsonl)
if ($SourceId) {
    $pyArgs += @("--source-id", $SourceId, "--nlm-bin", $NlmBin)
} else {
    $rp = if ([System.IO.Path]::IsPathRooted($RawPath)) { $RawPath } else { Join-Path $RepoRoot $RawPath }
    $pyArgs += @("--in", (Resolve-Path -LiteralPath $rp).Path)
}
if ($IngestReport) {
    $ir = if ([System.IO.Path]::IsPathRooted($IngestReport)) { $IngestReport } else { Join-Path $RepoRoot $IngestReport }
    $pyArgs += @("--report", $ir)
}

Write-Host "[nl_metabolism_ingest] $PythonExe $($pyArgs -join ' ')"
& $PythonExe @pyArgs
if ($LASTEXITCODE -ne 0) {
    throw "ingest_notebooklm_metabolism_jsonl.py failed (exit $LASTEXITCODE)"
}

if ($SkipAblationChain) {
    Write-Host "SkipAblationChain: done at $OutJsonl"
    exit 0
}

if (-not $AblationOutDir) {
    $AblationOutDir = Join-Path $RepoRoot "docs\final\artifacts\log_ablation_chain_nl_metabolism_v1"
} elseif (-not [System.IO.Path]::IsPathRooted($AblationOutDir)) {
    $AblationOutDir = Join-Path $RepoRoot $AblationOutDir
}

$chain = Join-Path $RepoRoot "scripts\run_log_ablation_chain_v1.ps1"
$chainArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $chain,
    "-OutDir", $AblationOutDir,
    "-MetabolismJsonl", $OutJsonl
)
if ($InputSpec) {
    $is = if ([System.IO.Path]::IsPathRooted($InputSpec)) { $InputSpec } else { Join-Path $RepoRoot $InputSpec }
    $chainArgs += @("-InputSpec", (Resolve-Path -LiteralPath $is).Path)
}
if ($SkipStaging) { $chainArgs += "-SkipStaging" }
if ($SkipCopyShard) { $chainArgs += "-SkipCopyShard" }
if ($SkipV4) { $chainArgs += "-SkipV4" }

Write-Host "[nl_metabolism_ingest] chain -> $AblationOutDir"
& powershell @chainArgs
if ($LASTEXITCODE -ne 0) {
    throw "run_log_ablation_chain_v1.ps1 failed (exit $LASTEXITCODE)"
}
exit 0
