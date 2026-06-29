# Hub (3010) + mkmlife (3105) local hot-reload pair — bootstrap env + optional verify.
param(
  [switch]$BootstrapEnv,
  [switch]$VerifyOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
$no1kmedi = Join-Path $root "projects\no1kmedi"
$mkmLife = Join-Path $root "projects\mkm\mkm-life"
$hubEnv = Join-Path $no1kmedi ".env.local"
$lifeEnv = Join-Path $mkmLife ".env.local"

$hubOriginLine = "NEXT_PUBLIC_MKMLIFE_ORIGIN=http://localhost:3105"
$openBetaLine = "MKM_ASK_ONE_OPEN_BETA=1"

function Ensure-EnvLine {
  param([string]$Path, [string]$Line, [string]$Key)
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType File -Path $Path -Force | Out-Null
  }
  $content = Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue
  $has = $content | Where-Object { $_ -match "^\s*$([regex]::Escape($Key))\s*=" }
  if ($has) {
    Write-Host "[hub-mkmlife-dev] $Key already in $(Split-Path -Leaf $Path)" -ForegroundColor DarkGray
    return
  }
  $needsNl = $false
  if ((Get-Item -LiteralPath $Path).Length -gt 0) {
    $tail = [System.IO.File]::ReadAllText($Path)
    if ($tail.Length -gt 0 -and -not $tail.EndsWith("`n")) { $needsNl = $true }
  }
  if ($needsNl) { Add-Content -LiteralPath $Path -Value "" -Encoding UTF8 -NoNewline:$false }
  Add-Content -LiteralPath $Path -Value $Line -Encoding UTF8
  Write-Host "[hub-mkmlife-dev] appended $Line -> $(Split-Path -Leaf $Path)" -ForegroundColor Green
}

if ($BootstrapEnv) {
  Ensure-EnvLine -Path $hubEnv -Line $hubOriginLine -Key "NEXT_PUBLIC_MKMLIFE_ORIGIN"
  Ensure-EnvLine -Path $lifeEnv -Line $openBetaLine -Key "MKM_ASK_ONE_OPEN_BETA"
}

Write-Host ""
Write-Host "Local hot-reload pair (restart dev servers after -BootstrapEnv):" -ForegroundColor Cyan
Write-Host "  1) cd projects\mkm\mkm-life && npm run dev    -> http://localhost:3105/ask-one"
Write-Host "  2) cd projects\no1kmedi && npm run dev        -> http://localhost:3010/hub"
Write-Host "  Hub life intent routes to localhost:3105 when NEXT_PUBLIC_MKMLIFE_ORIGIN is set."
Write-Host ""

if ($VerifyOnly -or $BootstrapEnv) {
  Push-Location $root
  try {
    & py -m pytest tests/test_mkmlife_hub_origin_v1.py tests/test_mkmlife_ask_one_open_beta_guest_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  } finally {
    Pop-Location
  }

  $hubUp = $false
  $lifeUp = $false
  try {
    $r1 = Invoke-WebRequest -Uri "http://localhost:3010/hub" -UseBasicParsing -TimeoutSec 3
    $hubUp = $r1.StatusCode -eq 200
  } catch {}
  try {
    $r2 = Invoke-WebRequest -Uri "http://localhost:3105/api/v1/config/ask-one" -UseBasicParsing -TimeoutSec 3
    $lifeUp = $r2.StatusCode -eq 200
  } catch {}

  Write-Host "[hub-mkmlife-dev] hub:3010=$hubUp mkmlife:3105=$lifeUp"
  if ($lifeUp) {
    $cfg = (Invoke-WebRequest -Uri "http://localhost:3105/api/v1/config/ask-one" -UseBasicParsing).Content
    Write-Host "[hub-mkmlife-dev] ask-one config: $cfg"
  }
}

exit 0
