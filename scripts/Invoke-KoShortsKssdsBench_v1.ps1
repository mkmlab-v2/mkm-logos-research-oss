# B-track KSSDS segment backend bench — isolated venv (transformers pin).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-KoShortsKssdsBench_v1.ps1
#   powershell -File scripts\Invoke-KoShortsKssdsBench_v1.ps1 -BootstrapVenv
#
param(
    [switch]$BootstrapVenv,
    [switch]$FixturesOnly,
    [int]$MaxChars = 28
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$VenvDir = Join-Path $Root '.venv-ko-shorts-kssds'
$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'
$Out = Join-Path $Root 'reports/ko_shorts_segment_backend_bench_kssds_v1_latest.json'

function Write-Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }

if ($BootstrapVenv -or -not (Test-Path -LiteralPath $VenvPy)) {
    Write-Step 'Creating .venv-ko-shorts-kssds (B-track isolated)'
    & py -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "venv create exit $LASTEXITCODE" }
    Write-Step 'pip install transformers==4.42.4 KSSDS kss in venv'
    & $VenvPy -m pip install -q --upgrade pip
    & $VenvPy -m pip install -q 'transformers==4.42.4' KSSDS kss
    if ($LASTEXITCODE -ne 0) { throw "pip install KSSDS stack exit $LASTEXITCODE" }
}

$benchArgs = @(
    'scripts/run_ko_shorts_segment_backend_bench_v1.py',
    '--include-kssds',
    '--max-chars', "$MaxChars",
    '--out', $Out
)
if ($FixturesOnly) { $benchArgs += '--fixtures-only' }

Write-Step 'run_ko_shorts_segment_backend_bench_v1.py (kssds venv)'
& $VenvPy @benchArgs
if ($LASTEXITCODE -ne 0) { throw "segment backend bench exit $LASTEXITCODE" }

Write-Host "OK: Invoke-KoShortsKssdsBench_v1 -> $Out" -ForegroundColor Green
exit 0
