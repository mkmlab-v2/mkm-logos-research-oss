<#
.SYNOPSIS
  B-track Day 1 (99% research lane): run three cap bands (mid / high / extreme) with fixed configs and logs.

.DESCRIPTION
  Research-only. Does not change production, Track A gates, or trading triggers.
  See docs/final/artifacts/BTRACK_99_PERCENT_COMPRESSION_EXECUTION_PLAN_V1.md Day 1.

.PARAMETER Quick
  Run one canonical config per band only (3 py invocations).

.PARAMETER IncludeDecoderMitigation
  After band runs, regenerate decoder loss mitigation benchmark artifact.

.PARAMETER OutRoot
  Parent folder for timestamped run folder under reports/constitution/btrack_pilot/

.NOTES
  Run from repo root:
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-BTrack99PercentDay1.ps1
#>
[CmdletBinding()]
param(
    [switch] $Quick,
    [switch] $IncludeDecoderMitigation,
    [string] $OutRoot = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $OutRoot) {
    $OutRoot = Join-Path $root "reports\constitution\btrack_pilot"
}
$ts = Get-Date -Format "yyyyMMddTHHmmssZ"
$runDir = Join-Path $OutRoot "btrack_day1_$ts"
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$logFile = Join-Path $runDir "day1_console.log"
function Write-Log([string]$msg) {
    $line = "$(Get-Date -Format o) $msg"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
    Write-Host $line
}

Write-Log "Run-BTrack99PercentDay1 start Quick=$Quick Out=$runDir"

# Deterministic-ish env note (evaluate_report may still use nondeterministic tie-breaks).
$env:PYTHONHASHSEED = "0"

$bands = @(
    @{
        id          = "mid"
        description = "Moderate caps toward Gate R2 phase 1"
        runs        = @(
            @{
                out             = "band_mid_weighted.json"
                poolSize        = 10
                selectionMode   = "weighted_score"
                fidelityWeight  = 0.90
                savingWeight    = 1.00
                integrityWeight = 1.50
                generalCap      = 0.56
                sensitiveCap    = 0.52
                hangulCap       = 0.50
            },
            @{
                out             = "band_mid_greedy.json"
                poolSize        = 10
                selectionMode   = "greedy_floor_first"
                fidelityWeight  = 1.00
                savingWeight    = 0.80
                integrityWeight = 1.60
                generalCap      = 0.56
                sensitiveCap    = 0.52
                hangulCap       = 0.50
                minJaccardGreedy = 0.85
            }
        )
    },
    @{
        id          = "high"
        description = "High caps aligned with prior cap62 exploration"
        runs        = @(
            @{
                out             = "band_high_cap62_like.json"
                poolSize        = 15
                selectionMode   = "weighted_score"
                fidelityWeight  = 0.65
                savingWeight    = 1.80
                integrityWeight = 2.00
                generalCap      = 0.62
                sensitiveCap    = 0.58
                hangulCap       = 0.56
            }
        )
    },
    @{
        id          = "extreme"
        description = "Aggressive caps for ceiling probe (integrity floor enforced)"
        runs        = @(
            @{
                out             = "band_extreme_weighted.json"
                poolSize        = 17
                selectionMode   = "weighted_score"
                fidelityWeight  = 0.55
                savingWeight    = 2.20
                integrityWeight = 2.00
                generalCap      = 0.72
                sensitiveCap    = 0.68
                hangulCap       = 0.65
            },
            @{
                out             = "band_extreme_pool20.json"
                poolSize        = 20
                selectionMode   = "weighted_score"
                fidelityWeight  = 0.50
                savingWeight    = 2.40
                integrityWeight = 2.10
                generalCap      = 0.78
                sensitiveCap    = 0.74
                hangulCap       = 0.70
            }
        )
    }
)

if ($Quick) {
    foreach ($b in $bands) {
        $b.runs = @($b.runs[0])
    }
}

function Invoke-E2Spike([hashtable]$cfg, [string]$outPath) {
    $args = @(
        "scripts/run_track_a_week22_e2_candidate_pool_spike_v1.py",
        "--out", $outPath,
        "--pool-size", "$($cfg.poolSize)",
        "--selection-mode", $cfg.selectionMode,
        "--fidelity-weight", "$($cfg.fidelityWeight)",
        "--saving-weight", "$($cfg.savingWeight)",
        "--integrity-weight", "$($cfg.integrityWeight)",
        "--general-max-saving-rate", "$($cfg.generalCap)",
        "--sensitive-max-saving-rate", "$($cfg.sensitiveCap)",
        "--hangul-max-saving-rate", "$($cfg.hangulCap)",
        "--saving-floor", "0",
        "--jaccard-floor", "0",
        "--integrity-floor", "1.0"
    )
    if ($cfg.minJaccardGreedy) {
        $args += @("--min-jaccard-for-greedy", "$($cfg.minJaccardGreedy)")
    }
    $p = Start-Process -FilePath "py" -ArgumentList $args -WorkingDirectory $root -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) {
        throw "E2 spike failed exit $($p.ExitCode): $($cfg.out)"
    }
}

$rows = @()
foreach ($band in $bands) {
    foreach ($run in $band.runs) {
        $outPath = Join-Path $runDir $run.out
        Write-Log "Band $($band.id) -> $($run.out)"
        Invoke-E2Spike $run $outPath
        $j = Get-Content $outPath -Raw | ConvertFrom-Json
        $rows += [PSCustomObject]@{
            band_id           = $band.id
            band_description  = $band.description
            artifact_relative = "reports/constitution/btrack_pilot/btrack_day1_$ts/$($run.out)"
            pool_size         = $run.poolSize
            selection_mode    = $run.selectionMode
            caps              = @{
                general   = $run.generalCap
                sensitive = $run.sensitiveCap
                hangul    = $run.hangulCap
            }
            saving            = [double]$j.metrics.global_token_saving_rate
            jaccard           = [double]$j.metrics.avg_reconstruction_fidelity_jaccard
            integrity         = [double]$j.metrics.avg_sensitive_integrity
            decision          = [string]$j.decision
        }
    }
}

if ($IncludeDecoderMitigation) {
    $decOut = Join-Path $runDir "decoder_loss_mitigation_benchmark_day1.json"
    Write-Log "Decoder mitigation benchmark -> $decOut"
    $p2 = Start-Process -FilePath "py" -ArgumentList @(
        "scripts/run_btrack_decoder_loss_mitigation_benchmark_v1.py",
        "--output", $decOut
    ) -WorkingDirectory $root -Wait -PassThru -NoNewWindow
    if ($p2.ExitCode -ne 0) {
        throw "decoder benchmark failed exit $($p2.ExitCode)"
    }
}

$best = $rows | Sort-Object @{ Expression = "integrity"; Descending = $true }, @{ Expression = "saving"; Descending = $true }, @{ Expression = "jaccard"; Descending = $true } | Select-Object -First 1

$summary = [ordered]@{
    schema               = "btrack_day1_three_band_summary_v1"
    generated_at_utc     = (Get-Date).ToUniversalTime().ToString("o")
    lane                 = "research_only"
    execution_plan_ref   = "docs/final/artifacts/BTRACK_99_PERCENT_COMPRESSION_EXECUTION_PLAN_V1.md"
    run_directory        = $runDir.Replace("\", "/")
    quick_mode           = [bool]$Quick
    python_hash_seed     = "0"
    rows                 = @($rows | ForEach-Object { $_ })
    best_row             = $best
    reached_integrity_1  = ($rows | Where-Object { $_.integrity -ge 1.0 }).Count -gt 0
}

$sumPathArtifacts = Join-Path $root "docs\final\artifacts\btrack_day1_three_band_summary_latest.json"
$summaryJson = $summary | ConvertTo-Json -Depth 8
Set-Content -Path $sumPathArtifacts -Value $summaryJson -Encoding UTF8
Copy-Item -Path $sumPathArtifacts -Destination (Join-Path $runDir "btrack_day1_three_band_summary.json") -Force

Write-Log "WROTE $sumPathArtifacts"
Write-Log "Run-BTrack99PercentDay1 done best saving=$($best.saving) integrity=$($best.integrity)"
