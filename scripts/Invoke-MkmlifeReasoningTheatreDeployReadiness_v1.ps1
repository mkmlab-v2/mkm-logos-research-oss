#requires -Version 5.1
<#
.SYNOPSIS
  Reasoning Theatre deploy readiness — pytest, static embed, optional local probe.
.EXAMPLE
  powershell -File scripts/Invoke-MkmlifeReasoningTheatreDeployReadiness_v1.ps1
  powershell -File scripts/Invoke-MkmlifeReasoningTheatreDeployReadiness_v1.ps1 -IncludeLocalProbe
#>
param(
  [switch]$IncludeLocalProbe,
  [string]$BaseUrl = $(if ($env:MKMLIFE_DEV_URL) { $env:MKMLIFE_DEV_URL } else { 'http://127.0.0.1:3105' })
)

$ErrorActionPreference = 'Stop'
$root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not (Test-Path (Join-Path $root 'projects\mkm\mkm-life\package.json'))) {
  $root = 'C:\workspace'
}

py (Join-Path $root 'scripts\build_magic_orb_reasoning_theatre_v1.py') --active-step ingest | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py -m pytest (Join-Path $root 'tests\test_magic_orb_reasoning_theatre_v1.py') -q --tb=no
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$static = Join-Path $root 'projects\mkm\mkm-life\public\data\magic_orb_question_insight_v1_latest.json'
if (-not (Test-Path $static)) {
  Write-Error "missing static insight: $static"
}
$theatreJson = Join-Path $root 'projects\mkm\mkm-life\public\data\magic_orb_reasoning_theatre_v1_latest.json'
if (-not (Test-Path $theatreJson)) {
  Write-Error "missing static theatre: $theatreJson"
}

if ($IncludeLocalProbe) {
  powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Invoke-MkmlifeReasoningTheatreSmoke_v1.ps1') -BaseUrl $BaseUrl
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host '[reasoning-theatre-deploy-readiness] ok — deploy mkmlife via deploy-to-hostinger.ps1 (human gate)'
exit 0
