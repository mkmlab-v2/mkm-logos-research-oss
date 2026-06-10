<#
.SYNOPSIS
  MusicGen 32s hub loop smoke — conditioning build + external batch (+ optional gate).

.DESCRIPTION
  B-track [HYPO]. Aligns with seed target_loop_seconds (default tension_sasang_01 = 32s).
  -DryRunOnly: musicgen --dry-run only (no GPU, no WAV).
  Default: full generate + gate when CUDA available; fails fast if external script missing.

.EXAMPLE
  pwsh -File scripts\Run-MusicGenLoop32Smoke_v1.ps1 -DryRunOnly
  pwsh -File scripts\Run-MusicGenLoop32Smoke_v1.ps1 -SkipGate
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SeedJson = "data/audio/seeds/tension_sasang_01.example.json",
    [string]$OutputDir = "workspace/audio_raw_economy/_musicgen_loop32_smoke",
    [switch]$DryRunOnly,
    [switch]$SkipGate
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$seedPath = Join-Path $WorkspaceRoot $SeedJson
$outRoot = Join-Path $WorkspaceRoot $OutputDir
$condPath = Join-Path $outRoot "tension_sasang_01.conditioning.json"
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null

Write-Host "[musicgen-32s] build conditioning -> $condPath"
& py (Join-Path $WorkspaceRoot "scripts\build_sasang_music_conditioning_from_seed_v1.py") `
    --seed-json $seedPath `
    --out-json $condPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$musicgen = Join-Path $WorkspaceRoot "scripts\audio\musicgen_external_generator_v1.py"
if (-not (Test-Path -LiteralPath $musicgen)) { throw "Missing: $musicgen" }

$env:MKM_AUDIO_CONDITIONING_JSON = $condPath
$env:MKM_AUDIO_EXTERNAL_SCRIPT = "scripts/audio/musicgen_external_generator_v1.py"
$env:MKM_AUDIO_MUSICGEN_NUMERIC_MODE = "melody"

if ($DryRunOnly) {
    $dryWav = Join-Path $outRoot "dry_run_probe.wav"
    & py $musicgen --seed-json $seedPath --out-wav $dryWav --dry-run --seconds 0
    exit $LASTEXITCODE
}

$batchArgs = @(
    "py", (Join-Path $WorkspaceRoot "scripts\audio\run_bgm_generation_batch.py"),
    "--seed-json", $seedPath,
    "--emit", "external",
    "--placeholder-seconds", "0",
    "--count", "1",
    "--output-dir", $OutputDir
)
if (-not $SkipGate) { $batchArgs += "--run-gate" }

Write-Host "[musicgen-32s] batch external (target_loop_seconds from seed)"
& $batchArgs[0] $batchArgs[1..($batchArgs.Length - 1)]
exit $LASTEXITCODE
