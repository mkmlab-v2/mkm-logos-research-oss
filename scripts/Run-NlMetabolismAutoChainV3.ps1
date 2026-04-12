#requires -version 5.1
<#
.SYNOPSIS
  run_nl_metabolism_auto_chain.ps1 with MULTILENS_PERFORMANCE_EVAL_INPUT_V3.json and stable OutDir naming.

.PARAMETER RepoRoot
  모노레포 루트 (기본: scripts 상위).

.PARAMETER AblationOutDir
  기본: docs/final/artifacts/log_ablation_chain_nl_auto_v3_<UTC-yyyyMMdd>

.PARAMETER SkipStaging / SkipCopyShard / SkipV4
  자동 체인에 그대로 전달.
#>
param(
    [string]$RepoRoot = "",
    [string]$AblationOutDir = "",
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

$inputSpec = Join-Path $RepoRoot "docs\final\artifacts\MULTILENS_PERFORMANCE_EVAL_INPUT_V3.json"
if (-not $AblationOutDir) {
    $day = (Get-Date).ToUniversalTime().ToString("yyyyMMdd")
    $AblationOutDir = "docs\final\artifacts\log_ablation_chain_nl_auto_v3_$day"
}

$chain = Join-Path $RepoRoot "scripts\run_nl_metabolism_auto_chain.ps1"
$args = @(
    "-File", $chain,
    "-InputSpec", $inputSpec,
    "-AblationOutDir", $AblationOutDir
)
if ($SkipStaging) { $args += "-SkipStaging" }
if ($SkipCopyShard) { $args += "-SkipCopyShard" }
if ($SkipV4) { $args += "-SkipV4" }

Write-Host "[Run-NlMetabolismAutoChainV3] $($args -join ' ')"
& powershell -NoProfile -ExecutionPolicy Bypass @args
exit $LASTEXITCODE
