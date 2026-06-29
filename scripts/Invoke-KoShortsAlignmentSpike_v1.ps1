# Ko shorts alignment backend spike — isolated venv for stable-ts (optional whisperx).
#
# Usage:
#   powershell -File scripts\Invoke-KoShortsAlignmentSpike_v1.ps1
#   powershell -File scripts\Invoke-KoShortsAlignmentSpike_v1.ps1 -Cases clinical_sim
#   powershell -File scripts\Invoke-KoShortsAlignmentSpike_v1.ps1 -IncludeWhisperx -BootstrapVenv
#
param(
    [string]$Cases = 'clinical_sim',
    [string]$Model = 'small',
    [string]$AlignmentBackend = 'auto',
    [string]$RoutingSidecar = '',
    [switch]$BootstrapVenv,
    [switch]$IncludeWhisperx
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$VenvDir = Join-Path $Root '.venv-ko-shorts-align'
$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'
$Out = Join-Path $Root 'reports/ko_shorts_alignment_backend_spike_v1_latest.json'

function Write-Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }

if ($BootstrapVenv -or -not (Test-Path -LiteralPath $VenvPy)) {
    Write-Step 'Creating .venv-ko-shorts-align'
    & py -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "venv create exit $LASTEXITCODE" }
    Write-Step 'pip install faster-whisper stable-ts'
    & $VenvPy -m pip install -q --upgrade pip
    & $VenvPy -m pip install -q faster-whisper stable-ts
    if ($LASTEXITCODE -ne 0) { throw "pip install align stack exit $LASTEXITCODE" }
    if ($IncludeWhisperx) {
        Write-Step 'pip install whisperx (optional, heavy)'
        & $VenvPy -m pip install -q whisperx
    }
}

$benchArgs = @(
    'scripts/run_ko_shorts_alignment_backend_spike_v1.py',
    '--cases', $Cases,
    '--model', $Model,
    '--alignment-backend', $AlignmentBackend,
    '--out', $Out
)
if ($RoutingSidecar) { $benchArgs += @('--routing-sidecar', $RoutingSidecar) }
if ($AlignmentBackend -eq 'bench_all') {
    $benchArgs += '--include-stable-ts'
    if ($IncludeWhisperx) { $benchArgs += '--include-whisperx' }
}

Write-Step 'run_ko_shorts_alignment_backend_spike_v1.py'
& $VenvPy @benchArgs
if ($LASTEXITCODE -ne 0) { throw "alignment spike exit $LASTEXITCODE" }

& py scripts/build_ko_shorts_segment_backend_decision_v1.py --alignment-spike $Out

Write-Host "OK: Invoke-KoShortsAlignmentSpike_v1 -> $Out" -ForegroundColor Green
exit 0
