# Clinician graph: Next dev + HTTP smoke (fixture envelope; no CDS Python chain required).
param(
  [int] $Port = 3022,
  [switch] $NoAutoPort,
  [switch] $SkipHttp
)

function Test-LocalPortHasListener([int] $listenPort) {
  try {
    $xs = @(Get-NetTCPConnection -LocalPort $listenPort -State Listen -ErrorAction SilentlyContinue)
    return $xs.Count -gt 0
  } catch { return $false }
}

function Test-TcpPortAvailable([int] $listenPort) {
  if (Test-LocalPortHasListener $listenPort) { return $false }
  $l = New-Object System.Net.Sockets.TcpListener ([System.Net.IPAddress]::Loopback, $listenPort)
  try { $l.Start(); return $true } catch { return $false } finally { try { $l.Stop() } catch { } }
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

Write-Host "[clinician-graph-smoke] npm run build"
npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SkipHttp) {
  Write-Host "[clinician-graph-smoke] OK (build only, -SkipHttp)"
  exit 0
}

if ($env:NO1KMEDI_CLINICIAN_GRAPH_SMOKE_PORT -match '^\d+$') { $Port = [int]$env:NO1KMEDI_CLINICIAN_GRAPH_SMOKE_PORT }
if (-not $NoAutoPort) {
  $chosen = Resolve-FreePort $Port
  if ($null -eq $chosen) { Write-Host "ERROR: no free port near $Port"; exit 3 }
  if ($chosen -ne $Port) { Write-Host "[clinician-graph-smoke] port $Port busy; using $chosen" }
  $Port = $chosen
}

$npx = (Get-Command npx.cmd -ErrorAction SilentlyContinue).Source
if (-not $npx) { $npx = (Get-Command npx -ErrorAction Stop).Source }
$proc = Start-Process -WorkingDirectory $root -FilePath $npx -ArgumentList @("next", "dev", "-p", "$Port") -PassThru -WindowStyle Hidden
try {
  $base = "http://127.0.0.1:$Port"
  $deadline = (Get-Date).AddSeconds(90)
  $ready = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri "$base/clinician" -UseBasicParsing -TimeoutSec 3
      if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
  }
  if (-not $ready) { Write-Host "ERROR: dev server not ready on $base"; exit 2 }
  Start-Sleep -Seconds 2
  $env:NO1KMEDI_BASE_URL = $base
  npm run smoke:clinician-graph-http
  exit $LASTEXITCODE
}
finally {
  if ($null -ne $proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
}
