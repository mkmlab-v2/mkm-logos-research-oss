# Batch target WAV — clinical_sim x3 + delegated custom inbox.
#
# Usage:
#   powershell -File scripts\Invoke-KoShortsTargetWavBatch_v1.ps1
#   powershell -File scripts\Invoke-KoShortsTargetWavBatch_v1.ps1 -DelegateOnly
#
param(
    [switch]$ClinicalSimOnly,
    [switch]$DelegateOnly,
    [switch]$NoRefetch,
    [string]$Profile = 'netflix_v16_pro'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$args = @('scripts/run_ko_shorts_target_wav_batch_v1.py', '--profile', $Profile)
if ($ClinicalSimOnly) { $args += '--clinical-sim-only' }
if ($DelegateOnly) { $args += '--delegate-only' }
if ($NoRefetch) { $args += '--no-refetch' }

Write-Host '==> run_ko_shorts_target_wav_batch_v1.py' -ForegroundColor Cyan
& py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'OK: reports/ko_shorts_target_wav_batch_v1_latest.json' -ForegroundColor Green
