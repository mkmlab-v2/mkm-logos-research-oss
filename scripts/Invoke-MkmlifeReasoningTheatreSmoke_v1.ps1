#requires -Version 5.1
<#
.SYNOPSIS
  Smoke mkmlife Reasoning Theatre SSE + insight embed (local dev).
.EXAMPLE
  powershell -File scripts/Invoke-MkmlifeReasoningTheatreSmoke_v1.ps1
  powershell -File scripts/Invoke-MkmlifeReasoningTheatreSmoke_v1.ps1 -BaseUrl http://127.0.0.1:3300
#>
param(
  [string]$BaseUrl = $(if ($env:MKMLIFE_DEV_URL) { $env:MKMLIFE_DEV_URL } else { 'http://127.0.0.1:3105' }),
  [string]$Query = '위기 가운데 언약의 안정과 신실'
)

$ErrorActionPreference = 'Stop'
$root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not (Test-Path (Join-Path $root 'projects\mkm\mkm-life\package.json'))) {
  $root = 'C:\workspace'
}
$mkmlife = Join-Path $root 'projects\mkm\mkm-life'
Push-Location $mkmlife
try {
  node ./scripts/smoke-magic-orb-reasoning-theatre-stream.mjs $BaseUrl $Query
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  py (Join-Path $root 'scripts\build_magic_orb_reasoning_theatre_v1.py') --active-step ingest | Out-Null
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  py -m pytest (Join-Path $root 'tests\test_magic_orb_reasoning_theatre_v1.py') -q --tb=no
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  py (Join-Path $root 'scripts\probe_mkmlife_reasoning_theatre_v1.py') --base-url $BaseUrl
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  exit 0
}
finally {
  Pop-Location
}
