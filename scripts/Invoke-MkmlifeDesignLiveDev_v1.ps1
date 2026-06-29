# MKMLIFE Design Lane local live loop - home + oracle-sphere.
param(
  [ValidateSet('home', 'oracle', 'all')]
  [string]$Lane = 'all',
  [switch]$SkipDevStart,
  [switch]$VerifyOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
$mkmLife = Join-Path $root 'projects\mkm\mkm-life'
$devUrl = 'http://127.0.0.1:3105'

function Test-DevUp {
  try {
    $r = Invoke-WebRequest -Uri "$devUrl/" -UseBasicParsing -TimeoutSec 8
    return $r.StatusCode -eq 200 -and $r.Content -match 'life-portal'
  } catch {
    return $false
  }
}

Write-Host "[mkmlife-design-live] lane=$Lane" -ForegroundColor Cyan
Write-Host "[mkmlife-design-live] home  -> $devUrl/" -ForegroundColor Cyan
Write-Host "[mkmlife-design-live] oracle -> $devUrl/oracle-sphere?live=1" -ForegroundColor Cyan

if (-not $SkipDevStart) {
  if (Test-DevUp) {
    Write-Host '[mkmlife-design-live] dev already up (portal healthy)' -ForegroundColor DarkGray
  } else {
    Write-Host '[mkmlife-design-live] dev:portal:restart (idempotent)...' -ForegroundColor Yellow
    Push-Location $mkmLife
    try {
      & node (Join-Path $mkmLife 'scripts\mkmlife-dev-port.mjs') restart
      if ($LASTEXITCODE -ne 0) { throw "dev:portal:restart exit $LASTEXITCODE" }
    } finally {
      Pop-Location
    }
    if (-not (Test-DevUp)) {
      Write-Error "dev server not reachable on $devUrl - run: cd projects\mkm\mkm-life; npm run dev:portal:restart"
    }
    Write-Host '[mkmlife-design-live] dev up' -ForegroundColor Green
  }
} elseif (-not (Test-DevUp)) {
  Write-Error "dev not running. Start: cd projects\mkm\mkm-life; npm run dev:portal:restart"
}

if ($VerifyOnly) {
  Push-Location $root
  try {
    & py -m pytest tests/test_mkmlife_design_live_dev_v1.py tests/test_oracle_sphere_live_dev_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  } finally {
    Pop-Location
  }
  Write-Host '[mkmlife-design-live] verify ok' -ForegroundColor Green
  exit 0
}

$npmScript = switch ($Lane) {
  'home'   { 'dev:mkmlife:home:live' }
  'oracle' { 'dev:oracle-sphere:live' }
  default  { 'dev:mkmlife:design:live' }
}

Write-Host "[mkmlife-design-live] watch: npm run $npmScript" -ForegroundColor Cyan
Push-Location $mkmLife
try {
  $env:MKMLIFE_DEV_URL = $devUrl
  & npm run $npmScript
} finally {
  Pop-Location
}
