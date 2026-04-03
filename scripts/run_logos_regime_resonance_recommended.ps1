# Recommended entry: full-corpus verse ranking by regime fingerprint only (31,102 canon lines).
# Does NOT take KOSPI or lemma-frequency inputs — see logos_vector_resonance_probe.py docstring.
# KOSPI baselines: scripts/run_chronos_forward_kospi_baseline.ps1
#
# Example:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_logos_regime_resonance_recommended.ps1 -Regime lehman -TopK 100

param(
    [string]$Regime = "lehman",
    [int]$TopK = 100,
    [string]$Output = "",
    [int]$Limit = 0
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $workspace

$safeRegime = ($Regime -replace '[^a-z0-9_\-]', '_')
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path (Join-Path $workspace "backtest_results") "LOGOS_RESONANCE_REGIME_${safeRegime}_TOP${TopK}.json"
}

$probe = Join-Path $workspace "scripts\logos_vector_resonance_probe.py"
$args = @(
    $probe,
    "--rank-by-regime",
    "--regime", $Regime,
    "--top-k", "$TopK",
    "--output", $Output
)
if ($Limit -gt 0) {
    $args += @("--limit", "$Limit")
}

Write-Host "[logos-regime-resonance] Regime=$Regime TopK=$TopK -> $Output" -ForegroundColor Cyan
& py @args
exit $LASTEXITCODE
