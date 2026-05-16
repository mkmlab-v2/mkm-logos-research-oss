# Clinician CDSS → patient_care_bundle: offline Node smokes + Next dev + HTTP strict chain.
#
# Env:
#   MKM_WORKSPACE_ROOT — monorepo root (default: parent of projects/no1kmedi)
#   NO1KMEDI_CLINICIAN_BUNDLE_SMOKE_PORT — dev port (default 3021)
param(
  [int] $Port = 3021,
  [switch] $NoAutoPort,
  [switch] $SkipHttp
)

function Test-LocalPortHasListener([int] $listenPort) {
  try {
    $xs = @(Get-NetTCPConnection -LocalPort $listenPort -State Listen -ErrorAction SilentlyContinue)
    return $xs.Count -gt 0
  } catch {
    return $false
  }
}

function Test-TcpPortAvailable([int] $listenPort) {
  if (Test-LocalPortHasListener $listenPort) { return $false }
  $l = New-Object System.Net.Sockets.TcpListener ([System.Net.IPAddress]::Loopback, $listenPort)
  try {
    $l.Start()
    return $true
  } catch {
    return $false
  } finally {
    try { $l.Stop() } catch { }
  }
}

function Resolve-FreePort([int] $startPort, [int] $maxTries = 50) {
  for ($i = 0; $i -lt $maxTries; $i++) {
    $p = $startPort + $i
    if (Test-LocalPortHasListener $p) { continue }
    if (Test-TcpPortAvailable $p) { return $p }
  }
  return $null
}

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$defaultMono = (Resolve-Path (Join-Path $root "..\..")).Path
$monoRoot = $env:MKM_WORKSPACE_ROOT
if (-not $monoRoot) {
  $monoRoot = $defaultMono
} else {
  $probe = Join-Path $monoRoot "scripts\build_km_physician_cds_assist_envelope_v1.py"
  if (-not (Test-Path $probe)) {
    Write-Host "[clinician-bundle-smoke] WARN: MKM_WORKSPACE_ROOT missing CDS scripts; using $defaultMono"
    $monoRoot = $defaultMono
  }
}
$env:MKM_WORKSPACE_ROOT = $monoRoot
Write-Host "[clinician-bundle-smoke] MKM_WORKSPACE_ROOT=$monoRoot"

Write-Host "[clinician-bundle-smoke] offline: smoke:km-cds-envelope-adapter"
npm run smoke:km-cds-envelope-adapter
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[clinician-bundle-smoke] offline: smoke:patient-care-bundle-from-cds"
npm run smoke:patient-care-bundle-from-cds
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SkipHttp) {
  Write-Host "[clinician-bundle-smoke] OK (offline only, -SkipHttp)"
  exit 0
}

if ($env:NO1KMEDI_CLINICIAN_BUNDLE_SMOKE_PORT -match '^\d+$') {
  $Port = [int]$env:NO1KMEDI_CLINICIAN_BUNDLE_SMOKE_PORT
}
$autoPort = -not $NoAutoPort
if ($autoPort) {
  $chosen = Resolve-FreePort $Port
  if ($null -eq $chosen) {
    Write-Host "[clinician-bundle-smoke] ERROR: no free port near $Port"
    exit 3
  }
  if ($chosen -ne $Port) { Write-Host "[clinician-bundle-smoke] port $Port busy; using $chosen" }
  $Port = $chosen
}

Write-Host "[clinician-bundle-smoke] starting Next.js on port $Port"
$npx = (Get-Command npx.cmd -ErrorAction SilentlyContinue).Source
if (-not $npx) { $npx = (Get-Command npx -ErrorAction Stop).Source }
$startSplat = @{
  WorkingDirectory = $root
  FilePath         = $npx
  ArgumentList     = @("next", "dev", "-p", "$Port")
  PassThru         = $true
}
$useHiddenWindow =
  ($PSVersionTable.PSEdition -eq 'Desktop') -or
  ($PSVersionTable.Platform -eq 'Win32NT')
if ($useHiddenWindow) {
  $proc = Start-Process @startSplat -WindowStyle Hidden
} else {
  $proc = Start-Process @startSplat
}
try {
  $base = "http://127.0.0.1:$Port"
  $deadline = (Get-Date).AddSeconds(90)
  $ready = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri "$base/" -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
  }
  if (-not $ready) {
    Write-Host "[clinician-bundle-smoke] ERROR: dev server not ready on $base"
    exit 2
  }
  Start-Sleep -Seconds 2
  $env:NO1KMEDI_BASE_URL = $base
  Write-Host "[clinician-bundle-smoke] NO1KMEDI_BASE_URL=$env:NO1KMEDI_BASE_URL"
  npm run smoke:clinician-cds-bundle-http:strict
  exit $LASTEXITCODE
}
finally {
  if ($null -ne $proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
}
