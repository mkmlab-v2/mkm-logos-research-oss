[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$WindowDays = 7
)

$ErrorActionPreference = "Stop"
$builder = Join-Path $WorkspaceRoot "scripts\build_mkm_three_lens_weekly_quality_report_v1.py"
if (-not (Test-Path -LiteralPath $builder)) {
    throw "Builder not found: $builder"
}

Set-Location -LiteralPath $WorkspaceRoot
& py -u $builder --window-days $WindowDays
exit $LASTEXITCODE
