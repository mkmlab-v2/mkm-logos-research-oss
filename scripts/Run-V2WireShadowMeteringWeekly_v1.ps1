#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly v2 wire shadow A/B (Golden boost cases, B-track only; active report untouched).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$MaxCases = 0,
    [switch]$AppendLog
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$pyExe = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $pyExe)) {
    $pyExe = "C:\Python311\python.exe"
}
if (-not (Test-Path -LiteralPath $pyExe)) {
    $pyExe = "py"
}

$appendArg = if ($AppendLog) { @("--append") } else { @() }
$maxArg = @("--max-cases", "$MaxCases")

& $pyExe scripts/run_v2_wire_shadow_metering_bench_v1.py @maxArg @appendArg
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $pyExe scripts/summarize_v2_wire_shadow_metering_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $pyExe scripts/comp_v2_wire_staging_promotion_scope_v1.py
exit $LASTEXITCODE
