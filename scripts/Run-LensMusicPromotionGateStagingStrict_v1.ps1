<#
.SYNOPSIS
  One-shot B-track lens music promotion gate with explicit M31 strict profile (audit-friendly).

.DESCRIPTION
  Wraps check_lens_music_symbolic_audio_promotion_gate_v1.py with --m31-profile strict and default
  hormone trend / output paths. Use for staging sign-off or CI-adjacent manual runs; daily fusion
  defaults remain strict unless -LensMusicPromotionGateSoftM31 is set on Invoke-TrackCMacroDailyFusion_v1.ps1.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-LensMusicPromotionGateStagingStrict_v1.ps1
#>
[CmdletBinding()]
param(
    [string]$OutJson = "",
    [string]$HormoneTrendJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

$gate = Join-Path $PSScriptRoot "check_lens_music_symbolic_audio_promotion_gate_v1.py"
if (-not (Test-Path -LiteralPath $gate)) {
    throw "Gate script not found: $gate"
}

$out = if (-not [string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson
} else {
    Join-Path $repoRoot "reports\lens_music_symbolic_audio_promotion_gate_staging_strict_latest.json"
}

$ht = if (-not [string]::IsNullOrWhiteSpace($HormoneTrendJson)) {
    $HormoneTrendJson
} else {
    Join-Path $repoRoot "docs\final\artifacts\lens_music_hormone_trend_latest.json"
}

py $gate --out $out --hormone-trend-json $ht --m31-profile strict
exit $LASTEXITCODE
