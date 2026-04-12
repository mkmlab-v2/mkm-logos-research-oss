#requires -version 5.1
<#
.SYNOPSIS
  LOG_METABOLISM ingest + ablation: local raw (optional) → NotebookLM discover → KPI fallback.

.DESCRIPTION
  0) Local 실탄 우선: -LocalRawPath, 또는 환경변수 MKM_LOG_METABOLISM_RAW_IN, 또는
     docs/final/artifacts/derived/inbox_log_metabolism_raw.txt (존재·비어 있지 않음)이면
     discover 생략 후 ingest_notebooklm_metabolism_jsonl --in 해당 파일 → 체인.
  1) Else: py scripts/discover_nl_metabolism_source.py --quiet
  2) If match: run_nl_metabolism_ingest_chain.ps1 -SourceId ...
     Else: run_nl_metabolism_ingest_chain.ps1 -RawPath -FallbackMetabolismJsonl (default KPI-derived)
  3) Writes docs/final/artifacts/derived/nl_metabolism_auto_chain_latest.json

.PARAMETER LocalRawPath
  로컬 원시 텍스트/보내기 경로(절대 또는 RepoRoot 기준). 설정 시 NotebookLM 스캔을 건너뜀.

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
    [string]$LocalRawPath = "",
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

$PythonExe = "py"
if ($env:MKM_PYTHON_EXE -and (Test-Path -LiteralPath $env:MKM_PYTHON_EXE)) {
    $PythonExe = $env:MKM_PYTHON_EXE
}

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

function Test-UsableRawFile {
    param([string]$LiteralPath)
    if (-not $LiteralPath) { return $false }
    if (-not (Test-Path -LiteralPath $LiteralPath -PathType Leaf)) { return $false }
    try {
        return ((Get-Item -LiteralPath $LiteralPath).Length -gt 0)
    } catch {
        return $false
    }
}

$defaultInbox = Join-Path $RepoRoot "docs\final\artifacts\derived\inbox_log_metabolism_raw.txt"
$candidate = ""
if ($LocalRawPath) {
    $candidate = if ([System.IO.Path]::IsPathRooted($LocalRawPath)) { $LocalRawPath } else { Join-Path $RepoRoot $LocalRawPath }
} elseif ($env:MKM_LOG_METABOLISM_RAW_IN) {
    $e = $env:MKM_LOG_METABOLISM_RAW_IN.Trim()
    $candidate = if ([System.IO.Path]::IsPathRooted($e)) { $e } else { Join-Path $RepoRoot $e }
} elseif (Test-UsableRawFile -LiteralPath $defaultInbox) {
    $candidate = $defaultInbox
}

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
$d = $null

if (Test-UsableRawFile -LiteralPath $candidate) {
    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    $mode = "local_raw"
    $d = [ordered]@{
        schema           = "discover_nl_metabolism_source_v1"
        match            = $null
        reason           = "local_raw_priority"
        local_raw        = $resolved
        probed_sources   = 0
        notebooks_scanned = @()
    }
    $chainArgs += @(
        "-RawPath", $resolved,
        "-OutJsonl", (Join-Path $RepoRoot $OutJsonl)
    )
} else {
    $discover = Join-Path $RepoRoot "scripts\discover_nl_metabolism_source.py"
    $discJson = (& $PythonExe $discover --quiet)
    if ($LASTEXITCODE -ne 0) {
        throw "discover_nl_metabolism_source.py failed (exit $LASTEXITCODE)"
    }
    $d = $discJson | ConvertFrom-Json

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
