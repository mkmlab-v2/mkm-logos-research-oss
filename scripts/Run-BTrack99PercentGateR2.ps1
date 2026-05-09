<#
.SYNOPSIS
  B-track Gate R2 phased sweep (research): probe saving toward 0.60+ with integrity floor 1.0 and optional quality floor.

.NOTES
  Research-only. Repo root:
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-BTrack99PercentGateR2.ps1
#>
[CmdletBinding()]
param(
    [float] $JaccardFloor = 0.85,
    [float] $IntegrityFloor = 1.0
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$ts = Get-Date -Format "yyyyMMddTHHmmssZ"
$runDir = Join-Path $root "reports\constitution\btrack_pilot\btrack_gate_r2_$ts"
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$env:PYTHONHASHSEED = "0"

# Phase toward Gate R2 (0.60–0.70): proportional caps, pool 15, cap62-like weights
$configs = @(
    @{ name = "r2_probe_g058"; g = 0.58; s = 0.54; h = 0.52; pool = 15; sav = 1.75; fid = 0.68; intw = 2.0 },
    @{ name = "r2_probe_g060"; g = 0.60; s = 0.56; h = 0.54; pool = 15; sav = 1.75; fid = 0.68; intw = 2.0 },
    @{ name = "r2_probe_g062"; g = 0.62; s = 0.58; h = 0.56; pool = 15; sav = 1.80; fid = 0.65; intw = 2.0 },
    @{ name = "r2_probe_g064"; g = 0.64; s = 0.60; h = 0.58; pool = 16; sav = 1.85; fid = 0.62; intw = 2.0 },
    @{ name = "r2_probe_g066"; g = 0.66; s = 0.62; h = 0.60; pool = 17; sav = 1.90; fid = 0.60; intw = 2.0 },
    @{ name = "r2_probe_g068"; g = 0.68; s = 0.64; h = 0.62; pool = 18; sav = 1.95; fid = 0.58; intw = 2.05 },
    @{ name = "r2_probe_g070"; g = 0.70; s = 0.66; h = 0.64; pool = 18; sav = 2.00; fid = 0.55; intw = 2.05 }
)

$rows = @()
foreach ($c in $configs) {
    $outPath = Join-Path $runDir "$($c.name).json"
    $pyArgs = @(
        "scripts/run_track_a_week22_e2_candidate_pool_spike_v1.py",
        "--out", $outPath,
        "--pool-size", "$($c.pool)",
        "--selection-mode", "weighted_score",
        "--fidelity-weight", "$($c.fid)",
        "--saving-weight", "$($c.sav)",
        "--integrity-weight", "$($c.intw)",
        "--general-max-saving-rate", "$($c.g)",
        "--sensitive-max-saving-rate", "$($c.s)",
        "--hangul-max-saving-rate", "$($c.h)",
        "--saving-floor", "0",
        "--jaccard-floor", "0",
        "--integrity-floor", "$IntegrityFloor"
    )
    $p = Start-Process -FilePath "py" -ArgumentList $pyArgs -WorkingDirectory $root -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) { throw "GateR2 $($c.name) failed $($p.ExitCode)" }
    $j = Get-Content $outPath -Raw | ConvertFrom-Json
    $gateR3 = [bool](
        [double]$j.metrics.avg_reconstruction_fidelity_jaccard -ge $JaccardFloor -and
        [double]$j.metrics.avg_sensitive_integrity -ge $IntegrityFloor
    )
    $rows += [PSCustomObject]@{
        name      = $c.name
        artifact  = "reports/constitution/btrack_pilot/btrack_gate_r2_$ts/$($c.name).json"
        saving    = [double]$j.metrics.global_token_saving_rate
        jaccard   = [double]$j.metrics.avg_reconstruction_fidelity_jaccard
        integrity = [double]$j.metrics.avg_sensitive_integrity
        decision  = [string]$j.decision
        gate_r3_quality_ok = $gateR3
        caps      = @{ general = $c.g; sensitive = $c.s; hangul = $c.h }
    }
}

$best = $rows | Sort-Object @{Expression = "saving"; Descending = $true}, @{Expression = "jaccard"; Descending = $true} | Select-Object -First 1
$summary = [ordered]@{
    schema               = "btrack_gate_r2_phase_sweep_v1"
    generated_at_utc     = (Get-Date).ToUniversalTime().ToString("o")
    lane                 = "research_only"
    jaccard_floor_ref    = $JaccardFloor
    integrity_floor_ref  = $IntegrityFloor
    run_directory        = $runDir.Replace("\", "/")
    rows                 = @($rows | ForEach-Object { $_ })
    best_row             = $best
    reached_saving_ge_060 = ($rows | Where-Object { $_.saving -ge 0.60 -and $_.integrity -ge 1.0 }).Count -gt 0
}

$outLatest = Join-Path $root "docs\final\artifacts\btrack_gate_r2_phase_sweep_latest.json"
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $outLatest -Encoding UTF8
Copy-Item $outLatest (Join-Path $runDir "btrack_gate_r2_phase_sweep.json") -Force
Write-Host "WROTE $outLatest best saving=$($best.saving) gate_r3_quality=$($best.gate_r3_quality_ok)"
