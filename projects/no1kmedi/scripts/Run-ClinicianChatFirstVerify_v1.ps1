# Chat-First clinician: health check → optional .next heal → API smokes + /clinician HTML smoke.
#
# Usage (repo projects/no1kmedi):
#   pwsh -NoProfile -File scripts/Run-ClinicianChatFirstVerify_v1.ps1
#   pwsh -NoProfile -File scripts/Run-ClinicianChatFirstVerify_v1.ps1 -SpawnDev   # isolated port, stop after
#   pwsh -NoProfile -File scripts/Run-ClinicianChatFirstVerify_v1.ps1 -SkipStrict
#
param(
  [int] $Port = 3010,
  [switch] $SpawnDev,
  [switch] $NoAutoPort,
  [switch] $SkipStrict,
  [switch] $SkipPageSmoke,
  [switch] $KeepDev
)

function Test-LocalPortHasListener([int] $listenPort) {
  try {
    return @((Get-NetTCPConnection -LocalPort $listenPort -State Listen -ErrorAction SilentlyContinue)).Count -gt 0
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

function Test-ClinicianSessionJson([string] $baseUrl) {
  $node = @"
fetch('$baseUrl/api/member/clinician-session',{signal:AbortSignal.timeout(12000)})
  .then(async r=>{const t=await r.text(); try{const j=JSON.parse(t); if(j.success){process.stdout.write('OK'); process.exit(0)} process.stderr.write('BAD '+t.slice(0,120)); process.exit(2)} catch{process.stderr.write('HTML '+r.status+' '+t.slice(0,80)); process.exit(2)}})
  .catch(e=>{process.stderr.write('DOWN '+e.message); process.exit(3)});
"@
  $prev = $LASTEXITCODE
  $out = node -e $node 2>&1
  $code = $LASTEXITCODE
  if ($code -eq 0) { return $true }
  Write-Host "[chat-first-verify] session probe fail: $out"
  return $false
}

function Stop-PortListener([int] $listenPort) {
  try {
    $procIds = @(Get-NetTCPConnection -LocalPort $listenPort -State Listen -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($procId in $procIds) {
      if ($procId -and $procId -gt 0) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      }
    }
  } catch { }
}

function Wait-PortListening([int] $listenPort, [int] $timeoutSec = 45) {
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    if (Test-LocalPortHasListener $listenPort) { return $true }
    Start-Sleep -Seconds 1
  }
  return $false
}

function Clear-NextCache([string] $root) {
  $next = Join-Path $root ".next"
  if (Test-Path $next) {
    Remove-Item -Recurse -Force $next -ErrorAction SilentlyContinue
    Write-Host "[chat-first-verify] cleared .next"
  }
}

function Start-NextDev([string] $root, [int] $listenPort) {
  # npx exits after delegating; run next CLI under node so the dev server stays alive.
  $node = (Get-Command node -ErrorAction Stop).Source
  $nextCli = Join-Path $root "node_modules\next\dist\bin\next"
  if (-not (Test-Path $nextCli)) {
    throw "missing $nextCli — run npm install in projects/no1kmedi"
  }
  $startSplat = @{
    WorkingDirectory = $root
    FilePath         = $node
    ArgumentList     = @($nextCli, "dev", "-p", "$listenPort")
    PassThru         = $true
    WindowStyle      = "Hidden"
  }
  # Child inherits MKM_WORKSPACE_ROOT / KM_CLINICIAN_DEV_UNLOCK from this session.
  return Start-Process @startSplat
}

function Wait-DevReady([string] $baseUrl, [int] $listenPort, [int] $timeoutSec = 120) {
  if (-not (Wait-PortListening $listenPort 45)) {
    Write-Host "[chat-first-verify] WARN: port $listenPort not listening yet"
  }
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    if ($null -ne $script:spawnedProc -and $script:spawnedProc.HasExited) {
      Write-Host "[chat-first-verify] ERROR: dev process exited early (code $($script:spawnedProc.ExitCode))"
      return $false
    }
    if (Test-ClinicianSessionJson $baseUrl) { return $true }
    Start-Sleep -Seconds 2
  }
  return $false
}

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$defaultMono = (Resolve-Path (Join-Path $root "..\..")).Path
if (-not $env:MKM_WORKSPACE_ROOT) {
  $env:MKM_WORKSPACE_ROOT = $defaultMono
} else {
  $probe = Join-Path $env:MKM_WORKSPACE_ROOT "scripts\build_km_physician_cds_assist_envelope_v1.py"
  if (-not (Test-Path $probe)) {
    Write-Host "[chat-first-verify] WARN: MKM_WORKSPACE_ROOT missing CDS scripts; using $defaultMono"
    $env:MKM_WORKSPACE_ROOT = $defaultMono
  }
}
if (-not $env:KM_CLINICIAN_DEV_UNLOCK) {
  $env:KM_CLINICIAN_DEV_UNLOCK = "1"
}
Write-Host "[chat-first-verify] MKM_WORKSPACE_ROOT=$($env:MKM_WORKSPACE_ROOT)"

$spawned = $null
$script:spawnedProc = $null
$ownedDev = $false
# Default: one-shot verify — spawn dev if nothing healthy on target port (no manual npx).
if (-not $PSBoundParameters.ContainsKey("SpawnDev")) {
  $SpawnDev = $true
}

try {
  if ($SpawnDev) {
    if (-not $NoAutoPort) {
      $chosen = Resolve-FreePort $Port
      if ($null -eq $chosen) {
        Write-Host "[chat-first-verify] ERROR: no free port near $Port"
        exit 3
      }
      if ($chosen -ne $Port) { Write-Host "[chat-first-verify] port $Port busy; using $chosen" }
      $Port = $chosen
    }
    Write-Host "[chat-first-verify] spawning Next dev on :$Port"
    $spawned = Start-NextDev $root $Port
    $script:spawnedProc = $spawned
    $ownedDev = $true
    if (-not (Wait-PortListening $Port 30)) {
      Write-Host "[chat-first-verify] ERROR: dev did not bind :$Port"
      exit 2
    }
  } else {
    $baseProbe = "http://127.0.0.1:$Port"
    if (-not (Test-ClinicianSessionJson $baseProbe)) {
      Write-Host "[chat-first-verify] heal: stop :$Port, clear .next, restart dev"
      Stop-PortListener $Port
      Start-Sleep -Seconds 2
      Clear-NextCache $root
      $spawned = Start-NextDev $root $Port
      $script:spawnedProc = $spawned
      $ownedDev = $true
    }
  }

  $base = "http://127.0.0.1:$Port"
  $env:NO1KMEDI_BASE_URL = $base
  Write-Host "[chat-first-verify] NO1KMEDI_BASE_URL=$base"

  if (-not (Wait-DevReady $base $Port)) {
    Write-Host "[chat-first-verify] ERROR: dev not healthy on $base"
    exit 2
  }

  Write-Host "[chat-first-verify] npm run verify:clinician-chat-first"
  npm run verify:clinician-chat-first
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  if (-not $SkipStrict) {
    Write-Host "[chat-first-verify] npm run smoke:clinician-cds-bundle-http:strict"
    npm run smoke:clinician-cds-bundle-http:strict
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }

  if (-not $SkipPageSmoke) {
    Write-Host "[chat-first-verify] node scripts/smoke-clinician-page.mjs"
    node ./scripts/smoke-clinician-page.mjs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }

  Write-Host "[chat-first-verify] OK"
  exit 0
}
finally {
  if ($ownedDev -and -not $KeepDev) {
    Stop-PortListener $Port
    if ($null -ne $spawned -and -not $spawned.HasExited) {
      Stop-Process -Id $spawned.Id -Force -ErrorAction SilentlyContinue
      Write-Host "[chat-first-verify] stopped spawned dev (pid $($spawned.Id))"
    }
  } elseif ($ownedDev -and $KeepDev) {
    Write-Host "[chat-first-verify] dev left running: http://127.0.0.1:$Port/clinician"
  }
}
