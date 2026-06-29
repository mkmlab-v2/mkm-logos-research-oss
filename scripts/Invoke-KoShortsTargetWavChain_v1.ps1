# P1 target WAV chain — auto-resolve OSS proxy WAV → spike → burn-in → validate.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-KoShortsTargetWavChain_v1.ps1
#   powershell -File scripts\Invoke-KoShortsTargetWavChain_v1.ps1 -CaseId web_pansori
#   powershell -File scripts\Invoke-KoShortsTargetWavChain_v1.ps1 -Wav reports\audio\my.wav
#
param(
    [string]$CaseId = '',
    [string]$Wav = '',
    [switch]$Auto,
    [switch]$Delegate,
    [string]$DelegationSidecar = '',
    [string]$Profile = 'netflix_v16_pro',
    [string]$DomainHint = '',
    [switch]$SkipBurn,
    [switch]$SkipAlignment,
    [switch]$NoRefetch
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$args = @('scripts/run_ko_shorts_target_wav_chain_v1.py', '--profile', $Profile)
if ($Auto -or (-not $Wav -and -not $CaseId -and -not $Delegate)) { $args += '--auto' }
if ($Delegate) { $args += '--delegate' }
if ($DelegationSidecar) { $args += @('--delegation-sidecar', $DelegationSidecar) }
if ($CaseId) { $args += @('--case-id', $CaseId) }
if ($Wav) { $args += @('--wav', $Wav) }
if ($DomainHint) { $args += @('--domain-hint', $DomainHint) }
if ($SkipBurn) { $args += '--skip-burn' }
if ($SkipAlignment) { $args += '--skip-alignment' }
if ($NoRefetch) { $args += '--no-refetch' }

Write-Host '==> run_ko_shorts_target_wav_chain_v1.py' -ForegroundColor Cyan
& py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'OK: reports/ko_shorts_target_wav_chain_v1_latest.json' -ForegroundColor Green
