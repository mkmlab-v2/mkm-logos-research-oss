# encounter-sequence-v1: Next dev + HTTP POST smoke (Track B · HOLD).
#
# Env:
#   MKM_WORKSPACE_ROOT — monorepo root (default: grandparent of projects/no1kmedi)
#   NO1KMEDI_ENCOUNTER_SEQUENCE_SMOKE_PORT — dev port (default 3022)
param(
  [int] $Port = 3022,
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
  $probe = Join-Path $monoRoot "scripts\run_encounter_sequence_clinician_api_chain_v1.py"
  if (-not (Test-Path $probe)) {
    Write-Host "[encounter-sequence-http-smoke] WARN: MKM_WORKSPACE_ROOT missing chain; using $defaultMono"
    $monoRoot = $defaultMono
  }
}
$env:MKM_WORKSPACE_ROOT = $monoRoot
Write-Host "[encounter-sequence-http-smoke] MKM_WORKSPACE_ROOT=$monoRoot"

if ($SkipHttp) {
  Write-Host "[encounter-sequence-http-smoke] OK (offline skip, -SkipHttp)"
  exit 0
}

if ($env:NO1KMEDI_ENCOUNTER_SEQUENCE_SMOKE_PORT -match '^\d+$') {
  $Port = [int]$env:NO1KMEDI_ENCOUNTER_SEQUENCE_SMOKE_PORT
}
$autoPort = -not $NoAutoPort
if ($autoPort) {
  $chosen = Resolve-FreePort $Port
  if ($null -eq $chosen) {
    Write-Host "[encounter-sequence-http-smoke] ERROR: no free port near $Port"
    exit 3
  }
  if ($chosen -ne $Port) { Write-Host "[encounter-sequence-http-smoke] port $Port busy; using $chosen" }
  $Port = $chosen
}

Write-Host "[encounter-sequence-http-smoke] starting Next.js on port $Port"
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
  $deadline = (Get-Date).AddSeconds(120)
  $ready = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri "$base/" -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
  }
  if (-not $ready) {
    Write-Host "[encounter-sequence-http-smoke] ERROR: dev server not ready on $base"
    exit 2
  }
  Start-Sleep -Seconds 3
  $env:NO1KMEDI_BASE_URL = $base
  Write-Host "[encounter-sequence-http-smoke] NO1KMEDI_BASE_URL=$env:NO1KMEDI_BASE_URL"
  npm run smoke:encounter-sequence-http
  exit $LASTEXITCODE
}
finally {
  if ($null -ne $proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
}
