# PersonaDiary Design Lane local live loop — Next HMR + watch smoke.
param(
  [switch]$SkipDevStart,
  [switch]$VerifyOnly,
  [switch]$OpenBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$no1k = Join-Path $root 'projects\no1kmedi'
$devUrl = 'http://127.0.0.1:3010'
$pdUrl = "$devUrl/personadiary"

function Test-PdDevUp {
  try {
    $r = Invoke-WebRequest -Uri $pdUrl -UseBasicParsing -TimeoutSec 10
    return $r.StatusCode -eq 200 -and $r.Content -match 'pd-moment-nation-hero'
  } catch {
    return $false
  }
}

Write-Host "[personadiary-design-live] $pdUrl" -ForegroundColor Cyan
Write-Host "[personadiary-design-live] HMR: edit src/components/personadiary/* — browser auto-refreshes" -ForegroundColor DarkGray

if (-not $SkipDevStart) {
  if (Test-PdDevUp) {
    Write-Host '[personadiary-design-live] dev already up' -ForegroundColor DarkGray
  } else {
    Write-Host '[personadiary-design-live] starting npm run dev (background)...' -ForegroundColor Yellow
    Push-Location $no1k
    try {
      Start-Process -FilePath 'npm' -ArgumentList @('run', 'dev') -WorkingDirectory $no1k -WindowStyle Minimized
    } finally {
      Pop-Location
    }
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
      if (Test-PdDevUp) { break }
      Start-Sleep -Seconds 2
    }
    if (-not (Test-PdDevUp)) {
      Write-Error "dev not reachable on $pdUrl — run: cd projects\no1kmedi; npm run dev"
    }
    Write-Host '[personadiary-design-live] dev up' -ForegroundColor Green
  }
} elseif (-not (Test-PdDevUp)) {
  Write-Error "dev not running. Start: cd projects\no1kmedi; npm run dev"
}

if ($VerifyOnly) {
  Push-Location $root
  try {
    & py -m pytest tests/test_personadiary_live_dev_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  } finally {
    Pop-Location
  }
  Write-Host '[personadiary-design-live] verify ok' -ForegroundColor Green
  exit 0
}

if ($OpenBrowser) {
  Start-Process $pdUrl
}

Write-Host '[personadiary-design-live] watch: npm run dev:personadiary:live' -ForegroundColor Cyan
Push-Location $no1k
try {
  $env:NO1KMEDI_DEV_URL = $devUrl
  & npm run dev:personadiary:live
} finally {
  Pop-Location
}
