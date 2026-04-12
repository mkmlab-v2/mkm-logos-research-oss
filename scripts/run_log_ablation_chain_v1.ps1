#requires -version 5.1
<#
.SYNOPSIS
  Log-domain ablation chain: build staging shard → copy to codebook/shards → double multilens report → v4 Δ(global_real_saving_vs_raw).

.DESCRIPTION
  1) staging_shard_inference_run.py (heuristic by default; -UseLlm for Gemini)
  2) Copy docs/final/artifacts/staging_shards/zone_s_log_staging_v1.json → codebook/shards/zone_s_log_staging.json
  3) report_multilens_performance_eval: Control (natural routing)
  4) Same: Treatment (--force-shard-id zone_s_log_staging)
  5) calculate_integrity_cost_v4 on both reports; emit summary JSON with Δ = treatment − control
  Optional: -MetabolismJsonl cohort .jsonl → aggregate_log_metabolism_from_jsonl.py; summary gains metabolism_summary_path.

  Staging shard must exist in codebook/shards for --force-shard-id to resolve (route_from_shard_id).

.PARAMETER MetabolismJsonl
  Optional path to JSONL cohort (LOG_METABOLISM_COHORT_ROW_V1). Relative to RepoRoot if not rooted.

.PARAMETER MetabolismSummaryOut
  Optional output path for metabolism aggregate JSON (default: OutDir/log_metabolism_aggregate_v1.json).

.PARAMETER RepoRoot
  Repository root (default: parent of scripts/).

.PARAMETER SkipStaging
  Skip step 1; expect staging JSON already at -StagingArtifactPath.

.PARAMETER SkipCopyShard
  Skip copy to codebook/shards (treatment will fail if shard file missing).

.PARAMETER SkipV4
  Stop after multilens reports (no integrity v4). Still writes log_ablation_chain_summary_v1.json with v4_skipped=true and null v4 scalars.
#>
param(
    [string]$RepoRoot = "",
    [string]$InputSpec = "",
    [string]$OutDir = "",
    [string]$InferenceConfig = "",
    [string]$StagingArtifactPath = "",
    [string]$ShardId = "zone_s_log_staging",
    [ValidateSet("experimental", "baseline")]
    [string]$Mode = "experimental",
    [string]$Strategy = "C",
    [string]$Intensity = "high",
    [switch]$UseLlm,
    [switch]$SkipStaging,
    [switch]$SkipCopyShard,
    [switch]$SkipV4,
    [string]$MetabolismJsonl = "",
    [string]$MetabolismSummaryOut = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

Write-Host "[log_ablation_chain_v1] RepoRoot=$RepoRoot"

if (-not $InputSpec) {
    $InputSpec = Join-Path $RepoRoot "docs\final\artifacts\MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
}
if (-not $OutDir) {
    $OutDir = Join-Path $RepoRoot "docs\final\artifacts\log_ablation_chain"
}
if (-not $InferenceConfig) {
    $InferenceConfig = Join-Path $RepoRoot "docs\final\artifacts\inference_config_v1.json"
}
if (-not $StagingArtifactPath) {
    $StagingArtifactPath = Join-Path $RepoRoot "docs\final\artifacts\staging_shards\zone_s_log_staging_v1.json"
}

$null = New-Item -ItemType Directory -Force -Path $OutDir

$reportControl = Join-Path $OutDir "report_log_ablation_control_v1.json"
$reportTreatment = Join-Path $OutDir "report_log_ablation_treatment_v1.json"
$v4Control = Join-Path $OutDir "integrity_cost_v4_control_v1.json"
$v4Treatment = Join-Path $OutDir "integrity_cost_v4_treatment_v1.json"
$summaryOut = Join-Path $OutDir "log_ablation_chain_summary_v1.json"

$shardDest = Join-Path $RepoRoot "codebook\shards\$ShardId.json"

function Invoke-PyArgList {
    # Pass a single string array — do not splat the outer call into param([string[]]$Args) or only the first token binds.
    param([string[]]$ArgList)
    & py @ArgList
    if ($LASTEXITCODE -ne 0) {
        throw "py failed: py $($ArgList -join ' ') (exit $LASTEXITCODE)"
    }
}

function Get-RepoRelativePath {
    param([string]$FullPath)
    $f = (Resolve-Path -LiteralPath $FullPath).Path
    $r = $RepoRoot.TrimEnd('\', '/')
    $prefix = $r + '\'
    if ($f.StartsWith($prefix)) {
        return $f.Substring($prefix.Length).Replace('\', '/')
    }
    $prefix2 = $r + '/'
    if ($f.StartsWith($prefix2)) {
        return $f.Substring($prefix2.Length).Replace('\', '/')
    }
    return $f.Replace('\', '/')
}

# --- Stage 1: staging shard JSON ---
if (-not $SkipStaging) {
    Write-Host "[1/5] staging_shard_inference_run.py"
    $stagingArgs = @(
        (Join-Path $RepoRoot "scripts\staging_shard_inference_run.py"),
        "--config", $InferenceConfig,
        "--out", $StagingArtifactPath
    )
    if ($UseLlm) {
        $stagingArgs += "--llm"
    }
    Invoke-PyArgList -ArgList $stagingArgs
} else {
    Write-Host "[1/5] skip staging (SkipStaging)"
    if (-not (Test-Path -LiteralPath $StagingArtifactPath)) {
        throw "SkipStaging set but staging artifact missing: $StagingArtifactPath"
    }
}

# --- Stage 2: copy into codebook/shards (router load path) ---
Write-Host "[2/5] deploy staging shard -> codebook/shards"
if (-not $SkipCopyShard) {
    $shardsDir = Split-Path -Parent $shardDest
    $null = New-Item -ItemType Directory -Force -Path $shardsDir
    if (Test-Path -LiteralPath $shardDest) {
        $bak = "$shardDest.pre_log_ablation_$(Get-Date -Format 'yyyyMMddHHmmss').bak"
        Copy-Item -LiteralPath $shardDest -Destination $bak -Force
        Write-Host "Backed up existing shard to $bak"
    }
    Copy-Item -LiteralPath $StagingArtifactPath -Destination $shardDest -Force
    Write-Host "WROTE shard: $shardDest"
} else {
    Write-Host "SkipCopyShard: ensure $shardDest exists for treatment run."
}

$metabolismSummaryResolved = $null
if ($MetabolismJsonl) {
    Write-Host "[2b] aggregate_log_metabolism_from_jsonl (optional cohort)"
    $mjIn = if ([System.IO.Path]::IsPathRooted($MetabolismJsonl)) {
        $MetabolismJsonl
    } else {
        Join-Path $RepoRoot $MetabolismJsonl
    }
    $mjIn = (Resolve-Path -LiteralPath $mjIn).Path
    if (-not (Test-Path -LiteralPath $mjIn)) {
        throw "MetabolismJsonl not found: $mjIn"
    }
    if (-not $MetabolismSummaryOut) {
        $MetabolismSummaryOut = Join-Path $OutDir "log_metabolism_aggregate_v1.json"
    }
    $msOut = if ([System.IO.Path]::IsPathRooted($MetabolismSummaryOut)) {
        $MetabolismSummaryOut
    } else {
        Join-Path $RepoRoot $MetabolismSummaryOut
    }
    $aggScript = Join-Path $RepoRoot "scripts\aggregate_log_metabolism_from_jsonl.py"
    Invoke-PyArgList -ArgList @($aggScript, "--in", $mjIn, "--out", $msOut, "--config", $InferenceConfig)
    $metabolismSummaryResolved = (Resolve-Path -LiteralPath $msOut).Path
    Write-Host "  metabolism summary: $metabolismSummaryResolved"
}

$expId = ""
try {
    $cfg = Get-Content -LiteralPath $InferenceConfig -Raw -Encoding UTF8 | ConvertFrom-Json
    $expId = [string]$cfg.experiment_id
} catch { }

# --- Stage 3 & 4: multilens double probe ---
Write-Host "[3-4/5] report_multilens_performance_eval (control then treatment; experimental may take minutes on large inputs)"
$common = @(
    (Join-Path $RepoRoot "scripts\report_multilens_performance_eval.py"),
    "--input", $InputSpec,
    "--mode", $Mode,
    "--strategy", $Strategy,
    "--intensity", $Intensity,
    "--use-domain-router"
)
Invoke-PyArgList -ArgList @($common + @("--output", $reportControl))
Invoke-PyArgList -ArgList @($common + @("--output", $reportTreatment, "--force-shard-id", $ShardId))

$metabolismRel = $null
$metabolismJsonlRel = $null
if ($metabolismSummaryResolved) {
    $metabolismRel = Get-RepoRelativePath -FullPath $metabolismSummaryResolved
}
if ($MetabolismJsonl) {
    $mjSrc = if ([System.IO.Path]::IsPathRooted($MetabolismJsonl)) { $MetabolismJsonl } else { Join-Path $RepoRoot $MetabolismJsonl }
    $metabolismJsonlRel = Get-RepoRelativePath -FullPath $mjSrc
}

if ($SkipV4) {
    Write-Host "SkipV4: reports only (v4 not run). Control=$reportControl Treatment=$reportTreatment"
    if ($metabolismSummaryResolved) {
        Write-Host "  metabolism_summary: $metabolismSummaryResolved"
    }
    $summarySkip = [ordered]@{
        schema                  = "log_ablation_chain_summary_v1"
        v4_skipped              = $true
        experiment_id           = $expId
        shard_id                = $ShardId
        delta_s_real            = $null
        s_real_control_natural  = $null
        s_real_treatment_forced = $null
        metabolism_summary_path = $metabolismRel
        metabolism_jsonl_source = $metabolismJsonlRel
        note                    = "SkipV4: multilens control/treatment completed; calculate_integrity_cost_v4 not run. delta_s_real and s_real_* are null. When v4 runs, delta_s_real = treatment(forced shard) - control(natural); positive means forced log staging improved v4 real_saving_vs_raw vs natural routing. When metabolism_* set, correlate cohort scalars with this ablation run."
        paths                   = [ordered]@{
            input_spec       = $InputSpec
            staging_artifact = $StagingArtifactPath
            shard_deployed   = $shardDest
            report_control   = $reportControl
            report_treatment = $reportTreatment
            v4_control       = $v4Control
            v4_treatment     = $v4Treatment
        }
        generated_at_local      = (Get-Date).ToString("o")
    }
    ($summarySkip | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $summaryOut -Encoding UTF8
    Write-Host "  Summary: $summaryOut"
    exit 0
}

# --- Stage 5: integrity v4 ---
Write-Host "[5/5] calculate_integrity_cost_v4 (x2)"
$v4script = Join-Path $RepoRoot "scripts\calculate_integrity_cost_v4.py"
Invoke-PyArgList -ArgList @($v4script, "--report", $reportControl, "--input", $InputSpec, "--out", $v4Control)
Invoke-PyArgList -ArgList @($v4script, "--report", $reportTreatment, "--input", $InputSpec, "--out", $v4Treatment)

$jC = Get-Content -LiteralPath $v4Control -Raw -Encoding UTF8 | ConvertFrom-Json
$jT = Get-Content -LiteralPath $v4Treatment -Raw -Encoding UTF8 | ConvertFrom-Json
$sNatural = [double]$jC.summary.global_real_saving_vs_raw
$sForced = [double]$jT.summary.global_real_saving_vs_raw
$delta = $sForced - $sNatural

$summary = [ordered]@{
    schema                     = "log_ablation_chain_summary_v1"
    v4_skipped                 = $false
    experiment_id              = $expId
    shard_id                   = $ShardId
    delta_s_real               = $delta
    s_real_control_natural     = $sNatural
    s_real_treatment_forced    = $sForced
    metabolism_summary_path    = $metabolismRel
    metabolism_jsonl_source    = $metabolismJsonlRel
    note                       = "delta_s_real = treatment(forced shard) - control(natural); positive means forced log staging improved v4 real_saving_vs_raw vs natural routing. When metabolism_* set, correlate cohort scalars with this ablation run."
    paths                      = [ordered]@{
        input_spec       = $InputSpec
        staging_artifact = $StagingArtifactPath
        shard_deployed   = $shardDest
        report_control   = $reportControl
        report_treatment = $reportTreatment
        v4_control       = $v4Control
        v4_treatment     = $v4Treatment
    }
    generated_at_local         = (Get-Date).ToString("o")
}
($summary | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $summaryOut -Encoding UTF8

Write-Host ""
Write-Host "=== Log ablation chain (v4 global_real_saving_vs_raw) ==="
Write-Host ("  Control (natural):  {0:N6}" -f $sNatural)
Write-Host ("  Treatment (forced): {0:N6}" -f $sForced)
Write-Host ("  Delta (T-C):       {0:N6}" -f $delta)
Write-Host "  Summary: $summaryOut"
Write-Host ""

exit 0
