# Builds literature snapshot, starts Next.js on a free port, runs smoke:advanced-consult:literature, stops the server.
#
# Env (optional):
#   NO1KMEDI_LITERATURE_SMOKE_PORT     - initial port (default 3020)
#   NO1KMEDI_LITERATURE_SMOKE_NO_AUTO  - set to 1 to disable auto port scan (fixed Port only)
param(
  [int] $Port = 3020,
  [switch] $NoAutoPort
)

# Any LISTEN on this port (IPv4/IPv6). TcpListener-only checks missed :: listeners on Windows.
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

if ($env:NO1KMEDI_LITERATURE_SMOKE_PORT -match '^\d+$') {
  $Port = [int]$env:NO1KMEDI_LITERATURE_SMOKE_PORT
}

$autoPort = -not $NoAutoPort
if ($env:NO1KMEDI_LITERATURE_SMOKE_NO_AUTO -eq '1') { $autoPort = $false }

if ($autoPort) {
  $chosen = Resolve-FreePort $Port
  if ($null -eq $chosen) {
    Write-Host "[literature-smoke] ERROR: no free TCP port in range $Port..$($Port + 49) on 127.0.0.1"
    exit 3
  }
  if ($chosen -ne $Port) {
    Write-Host "[literature-smoke] port $Port busy; using $chosen"
  }
  $Port = $chosen
}

if ($NoAutoPort -and (Test-LocalPortHasListener $Port)) {
  Write-Host "[literature-smoke] ERROR: port $Port already in use (LISTEN). Stop the process or run without -NoAutoPort."
  exit 4
}

Write-Host "[literature-smoke] build:literature:memory"
npm run build:literature:memory
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[literature-smoke] starting Next.js on port $Port"
$npx = (Get-Command npx.cmd -ErrorAction SilentlyContinue).Source
if (-not $npx) { $npx = (Get-Command npx -ErrorAction Stop).Source }
# -WindowStyle is Windows-only; omit on Linux/macOS pwsh (CI).
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
  $deadline = (Get-Date).AddSeconds(60)
  $ready = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri "$base/" -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
  }
  if (-not $ready) {
    Write-Host "[literature-smoke] ERROR: dev server did not become ready on $base within 60s"
    exit 2
  }
  Start-Sleep -Seconds 2
  $env:NO1KMEDI_BASE_URL = $base
  Write-Host "[literature-smoke] NO1KMEDI_BASE_URL=$env:NO1KMEDI_BASE_URL"
  npm run smoke:advanced-consult:literature
  exit $LASTEXITCODE
}
finally {
  if ($null -ne $proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
}
