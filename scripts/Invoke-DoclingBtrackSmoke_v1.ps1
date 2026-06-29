# B-track Docling smoke — optional isolated venv (does not touch global site-packages).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-DoclingBtrackSmoke_v1.ps1
#   powershell -File scripts\Invoke-DoclingBtrackSmoke_v1.ps1 -BootstrapVenv
#   powershell -File scripts\Invoke-DoclingBtrackSmoke_v1.ps1 -FixtureOnly
#
param(
    [string]$InputPath = '',
    [switch]$BootstrapVenv,
    [switch]$FixtureOnly
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$VenvDir = Join-Path $Root '.venv-btrack-docling'
$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'

function Write-Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }

if ($BootstrapVenv -or -not (Test-Path -LiteralPath $VenvPy)) {
    Write-Step 'Creating .venv-btrack-docling (B-track isolated)'
    & py -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "venv create exit $LASTEXITCODE" }
    Write-Step 'pip install docling in venv'
    & $VenvPy -m pip install -q --upgrade pip
    & $VenvPy -m pip install -q docling
    if ($LASTEXITCODE -ne 0) { throw "pip install docling exit $LASTEXITCODE" }
}

$args = @('scripts/smoke_docling_btrack_v1.py')
if ($InputPath) { $args += @('--input', $InputPath) }
if ($FixtureOnly) { $args += '--fixture-only' }

Write-Step 'smoke_docling_btrack_v1.py'
& py @args
if ($LASTEXITCODE -ne 0) { throw "smoke_docling_btrack_v1.py exit $LASTEXITCODE" }

Write-Host 'OK: Invoke-DoclingBtrackSmoke_v1' -ForegroundColor Green
exit 0
