# Starts Next.js studio dev, runs workspace myeongni studio smoke chain (B-track, send_gate HOLD).
#
# Env:
#   MKM_WORKSPACE_ROOT              - monorepo root (default: parent of projects/no1kmedi)
#   NO1KMEDI_MYEONGNI_SMOKE_PORT    - initial port (default 3020)
#   NO1KMEDI_MYEONGNI_SMOKE_NO_AUTO - set to 1 for fixed port only
param(
  [int] $Port = 3020,
  [switch] $NoAutoPort,
  [switch] $SkipHttp,
  [switch] $SkipPlaywright
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
$no1kRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { Split-Path -Parent (Split-Path -Parent $no1kRoot) }
$chainPy = Join-Path $workspaceRoot "scripts\run_myeongni_studio_smoke_chain_v1.py"
if (-not (Test-Path -LiteralPath $chainPy)) {
  throw "Missing smoke chain: $chainPy"
}

$env:MKM_WORKSPACE_ROOT = $workspaceRoot

if ($SkipHttp) {
  Write-Host "[myeongni-studio-smoke] offline chain only"
  & py $chainPy --skip-http
  exit $LASTEXITCODE
}

if ($env:NO1KMEDI_MYEONGNI_SMOKE_PORT -match '^\d+$') {
  $Port = [int]$env:NO1KMEDI_MYEONGNI_SMOKE_PORT
}

$autoPort = -not $NoAutoPort
if ($env:NO1KMEDI_MYEONGNI_SMOKE_NO_AUTO -eq '1') { $autoPort = $false }

if ($autoPort) {
  $chosen = Resolve-FreePort $Port
  if ($null -eq $chosen) {
    Write-Host "[myeongni-studio-smoke] ERROR: no free TCP port in range $Port..$($Port + 49)"
    exit 3
  }
  if ($chosen -ne $Port) {
    Write-Host "[myeongni-studio-smoke] port $Port busy; using $chosen"
  }
  $Port = $chosen
} elseif (Test-LocalPortHasListener $Port) {
  Write-Host "[myeongni-studio-smoke] ERROR: port $Port already in use"
  exit 4
}

Set-Location $no1kRoot
Write-Host "[myeongni-studio-smoke] starting Next.js on port $Port"
$npx = (Get-Command npx.cmd -ErrorAction SilentlyContinue).Source
if (-not $npx) { $npx = (Get-Command npx -ErrorAction Stop).Source }
$startSplat = @{
  WorkingDirectory = $no1kRoot
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
      $r = Invoke-WebRequest -Uri "$base/myeongni-research/studio" -UseBasicParsing -TimeoutSec 3
      if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
  }
  if (-not $ready) {
    Write-Host "[myeongni-studio-smoke] ERROR: dev server not ready on $base within 90s"
    exit 2
  }

  $apiReady = $false
  $apiDeadline = (Get-Date).AddSeconds(120)
  $probeBody = @{
    query    = "smoke"
    year     = 1991
    month    = 3
    day      = 10
    hour     = 11
    minute   = 10
    tz       = "Asia/Seoul"
    is_male  = $true
    is_solar = $true
  } | ConvertTo-Json -Compress
  while ((Get-Date) -lt $apiDeadline) {
    try {
      $api = Invoke-WebRequest `
        -Uri "$base/api/myeongni/studio-mindmap-v1" `
        -Method POST `
        -Body $probeBody `
        -ContentType "application/json" `
        -UseBasicParsing `
        -TimeoutSec 30
      if ($api.StatusCode -eq 200) {
        $parsed = $api.Content | ConvertFrom-Json
        if ($parsed.success -eq $true) {
          $apiReady = $true
          break
        }
      }
    } catch { }
    Start-Sleep -Seconds 2
  }
  if (-not $apiReady) {
    Write-Host "[myeongni-studio-smoke] ERROR: studio-mindmap API not ready on $base within 120s"
    exit 5
  }

  Start-Sleep -Seconds 1
  $env:NO1KMEDI_BASE_URL = $base
  Write-Host "[myeongni-studio-smoke] MKM_WORKSPACE_ROOT=$workspaceRoot NO1KMEDI_BASE_URL=$base"
  & py $chainPy --base-url $base
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  if (-not $SkipPlaywright) {
    Write-Host "[myeongni-studio-smoke] playwright packaging guard"
    npm run smoke:myeongni-studio-mindmap-playwright
    exit $LASTEXITCODE
  }
  exit 0
} finally {
  if ($null -ne $proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
}
