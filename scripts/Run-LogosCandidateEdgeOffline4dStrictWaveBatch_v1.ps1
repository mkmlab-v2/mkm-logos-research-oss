# Run offline_4d strict wave batch (defer-only). [HYPO] B-track.
param(
    [int]$StartWave = 17,
    [int]$EndWave = 101,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = @('scripts/run_logos_candidate_edge_offline_4d_strict_wave_batch_v1.py', '--start-wave', "$StartWave", '--end-wave', "$EndWave")
if ($DryRun) { $py += '--dry-run' }
& py @py
exit $LASTEXITCODE
