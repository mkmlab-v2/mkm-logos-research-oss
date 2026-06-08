#Requires -Version 5.1
<#
.SYNOPSIS
  One-click A2A target points pilot bundle (tp01–tp03 + SSOT refresh).

.DESCRIPTION
  [HYPO] / research_only / B-track. Runs resume A2A pilot, lexicon_dense bench,
  Track C pointer pilot, rebuilds a2a_target_points_v1_latest.json.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-A2aTargetPointsPilotBundle_v1.ps1

.EXAMPLE
  powershell ... -IncludeSlice -IncludePytest
#>
param(
    [switch]$IncludeSlice,
    [int]$SliceMaxChars = 1200,
    [switch]$IncludePytest,
    [switch]$StrictExit
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$argsList = @("py", "scripts/build_a2a_target_points_pilot_bundle_v1.py")
if ($IncludeSlice) {
    $argsList += @("--include-slice", "--slice-max-chars", "$SliceMaxChars")
}
if ($IncludePytest) {
    $argsList += "--include-pytest"
}
if ($StrictExit) {
    $argsList += "--strict-exit"
}

Write-Host "== A2A target points pilot bundle (tp01-tp03) [HYPO] ==" -ForegroundColor Cyan
Write-Host ($argsList -join " ")
& $argsList[0] $argsList[1..($argsList.Length - 1)]
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] A2A target points pilot bundle OK" -ForegroundColor Green
