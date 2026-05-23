#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel L1 bundle: validate feedback JSONL + build evolution health (B-track).
#>
param(
  [int]$WindowDays = 7,
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[personal-insight-evolution] agg dir ensure"
$agg = Join-Path $root "reports\personal_insight_evolution"
New-Item -ItemType Directory -Force -Path $agg | Out-Null

Write-Host "[personal-insight-evolution] build health"
$strictArg = if ($Strict) { "--strict" } else { "" }
py scripts/build_personal_insight_evolution_health_v1.py --window-days $WindowDays $strictArg
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[personal-insight-evolution] pytest smoke"
py -m pytest tests/test_personal_insight_evolution_feedback_v1.py -q
exit $LASTEXITCODE
