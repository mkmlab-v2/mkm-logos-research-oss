# B-track Sherpa-ONNX STT smoke — isolated venv + audit log append.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-SherpaOnnxSttBtrackSmoke_v1.ps1
#   powershell -File scripts\Invoke-SherpaOnnxSttBtrackSmoke_v1.ps1 -BootstrapVenv
#   powershell -File scripts\Invoke-SherpaOnnxSttBtrackSmoke_v1.ps1 -FixtureOnly
#
param(
    [string]$WavPath = '',
    [switch]$BootstrapVenv,
    [switch]$FixtureOnly
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$VenvDir = Join-Path $Root '.venv-btrack-sherpa-onnx'
$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'

function Write-Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }

if ($BootstrapVenv -or -not (Test-Path -LiteralPath $VenvPy)) {
    Write-Step 'Creating .venv-btrack-sherpa-onnx (B-track isolated)'
    & py -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "venv create exit $LASTEXITCODE" }
    Write-Step 'pip install sherpa-onnx soundfile numpy in venv'
    & $VenvPy -m pip install -q --upgrade pip
    & $VenvPy -m pip install -q sherpa-onnx soundfile numpy jsonschema
    if ($LASTEXITCODE -ne 0) { throw "pip install sherpa-onnx exit $LASTEXITCODE" }
}

$args = @('scripts/smoke_sherpa_onnx_stt_btrack_v1.py')
if ($WavPath) { $args += @('--wav', $WavPath) }
if ($FixtureOnly) { $args += '--fixture-only' }

Write-Step 'smoke_sherpa_onnx_stt_btrack_v1.py'
& py @args
if ($LASTEXITCODE -ne 0) { throw "smoke_sherpa_onnx_stt_btrack_v1.py exit $LASTEXITCODE" }

Write-Host 'OK: Invoke-SherpaOnnxSttBtrackSmoke_v1' -ForegroundColor Green
exit 0
