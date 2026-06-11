#Requires -Version 5.1
<#
.SYNOPSIS
  Local-first GPU weekly routine (Azure HOLD): CPU gates + optional RTX MusicGen + Kaggle smoke check.

.DESCRIPTION
  Tier 0 default (no cloud GPU):
  1) Azure support ticket sync (passive)
  2) Kaggle Nemotron fast-smoke gate JSON check (no kernel push)
  3) Dynamic BGM hp sweep conditioning-only + counsel sample stage + ZIP
  4) Optional: -IncludeGpuRecommendedBundle (Control-Integrity oracle + Pack 0-B pytest)

  Tier 0 + local CUDA (optional -IncludeAudioGenerate):
  5) MusicGen melody regen for hp 0.2 / 0.5 / 1.0 (8s clips) then re-stage counsel WAVs

  Optional -IncludeMusicGenLoop32Smoke (local CUDA ~7–10 min):
  5b) Run-MusicGenLoop32Smoke_v1.ps1 — 32s hub loop + audio gate (B-track [HYPO])

  Optional -IncludeMediaThinSliceBake (CPU ffmpeg + media observability; pairs with audio bake):
  6) build_lens_btrack_playback_lut_matrix_v1.py (12 pairs) -> build_lens_btrack_audio_loops_v1.py
     -> build_lens_btrack_video_loops_v1.py -> build_showroom_lens_media_observability_v1.py

  Tier 2 optional (-IncludeKaggleLocalPrep): notebook sync + prep + dry-run only (no -AllowKernelPush).

  B-track [HYPO] · no Track A / live trading / Azure VM provision.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LocalGpuWeeklyRoutine_v1.ps1

.EXAMPLE
  powershell ... -File scripts\Run-LocalGpuWeeklyRoutine_v1.ps1 -IncludeAudioGenerate
#>
param(
    [switch]$IncludeAudioGenerate,
    [switch]$IncludeMusicGenLoop32Smoke,
    [switch]$IncludeMediaThinSliceBake,
    [switch]$IncludeKaggleLocalPrep,
    [switch]$IncludeGpuRecommendedBundle,
    [switch]$SkipAzureSync,
    [switch]$SkipCounselZip,
    [switch]$WhatIfPlan,
    [string]$WorkspaceRoot = "",
    [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

Set-Location $resolvedRoot

if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $resolvedRoot "reports\local_gpu_weekly_routine_v1_latest.json"
}

$steps = [System.Collections.Generic.List[object]]::new()
$started = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

function Add-Step {
    param(
        [string]$Id,
        [string]$Phase,
        [int]$ExitCode,
        [string]$Note = ""
    )
    $steps.Add([ordered]@{
            id         = $Id
            phase      = $Phase
            exit_code  = $ExitCode
            ok         = ($ExitCode -eq 0)
            note       = $Note
            finished_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        }) | Out-Null
}

function Invoke-PyStep {
    param(
        [string]$Id,
        [string]$Phase,
        [string[]]$PyArgs
    )
    if ($WhatIfPlan) {
        Add-Step -Id $Id -Phase $Phase -ExitCode 0 -Note ("plan: py " + ($PyArgs -join ' '))
        return
    }
    Write-Host "`n[$Phase] $Id" -ForegroundColor Cyan
    & py @PyArgs
    $ec = $LASTEXITCODE
    Add-Step -Id $Id -Phase $Phase -ExitCode $ec
    if ($ec -ne 0) { throw "Step failed: $Id (exit $ec)" }
}

function Invoke-PsStep {
    param(
        [string]$Id,
        [string]$Phase,
        [string]$ScriptRel,
        [string[]]$ExtraArgs = @()
    )
    $scriptPath = Join-Path $resolvedRoot $ScriptRel
    if ($WhatIfPlan) {
        Add-Step -Id $Id -Phase $Phase -ExitCode 0 -Note ("plan: " + $ScriptRel)
        return
    }
    Write-Host "`n[$Phase] $Id" -ForegroundColor Cyan
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $scriptPath) + $ExtraArgs
    & powershell @argList
    $ec = $LASTEXITCODE
    Add-Step -Id $Id -Phase $Phase -ExitCode $ec
    if ($ec -ne 0) { throw "Step failed: $Id (exit $ec)" }
}

$plan = [ordered]@{
    azure_sync            = -not $SkipAzureSync
    kaggle_gate_check     = $true
    hp_sweep_conditioning = $true
    counsel_stage_zip     = -not $SkipCounselZip
    audio_generate            = [bool]$IncludeAudioGenerate
    musicgen_loop32_smoke       = [bool]$IncludeMusicGenLoop32Smoke
    media_thin_slice_bake     = [bool]$IncludeMediaThinSliceBake
    kaggle_local_prep     = [bool]$IncludeKaggleLocalPrep
    gpu_recommended       = [bool]$IncludeGpuRecommendedBundle
}

if ($WhatIfPlan) {
    Write-Host ($plan | ConvertTo-Json -Depth 3)
    Add-Step -Id "plan_only" -Phase "plan" -ExitCode 0
}
else {
    if (-not $SkipAzureSync) {
        Invoke-PsStep -Id "azure_support_ticket_sync" -Phase "passive" `
            -ScriptRel "scripts\Invoke-AzureSupportTicketSync_v1.ps1"
    }

    if (-not $WhatIfPlan) {
        $kgGate = Join-Path $resolvedRoot "reports\kaggle_nemotron_fast_smoke_gate_v28_latest.json"
        $kgOk = $false
        $kgStatus = "missing"
        if (Test-Path -LiteralPath $kgGate) {
            $kgDoc = Get-Content -LiteralPath $kgGate -Raw | ConvertFrom-Json
            $kgStatus = [string]$kgDoc.gate_status
            $kgOk = ($kgStatus -eq "pass")
        }
        Add-Step -Id "kaggle_fast_smoke_gate_v28" -Phase "check" -ExitCode 0 `
            -Note ("gate_status=" + $kgStatus + "; pass=" + $kgOk)
        if (-not $kgOk) {
            Write-Warning "Kaggle fast-smoke gate not pass — run Invoke-KaggleNemotronTrainOnKaggle_v1.ps1 -AllowKernelPush when ready (human gate)."
        }
    }

    Invoke-PyStep -Id "hp_sweep_conditioning_only" -Phase "cpu" -PyArgs @(
        "scripts/run_dynamic_bgm_hp_sweep_v1.py", "--conditioning-only"
    )

    if (-not $SkipCounselZip) {
        Invoke-PyStep -Id "stage_audio_hook_samples" -Phase "cpu" -PyArgs @(
            "scripts/stage_track_c_audio_hook_samples_for_counsel_v1.py"
        )
        Invoke-PyStep -Id "counsel_export_manifest" -Phase "cpu" -PyArgs @(
            "scripts/build_track_c_b2b_counsel_export_manifest_v1.py", "--fail-if-missing"
        )
        Invoke-PyStep -Id "counsel_export_zip" -Phase "cpu" -PyArgs @(
            "scripts/build_track_c_b2b_counsel_zip_pack_v1.py"
        )
    }

    if ($IncludeAudioGenerate) {
        $env:MKM_AUDIO_EXTERNAL_SCRIPT = "scripts/audio/musicgen_external_generator_v1.py"
        $env:MKM_AUDIO_MUSICGEN_NUMERIC_MODE = "melody"
        if (-not $env:MKM_AUDIO_TORCH_SEED) { $env:MKM_AUDIO_TORCH_SEED = "42" }
        foreach ($hp in @("0.2", "0.5", "1.0")) {
            $tag = ("hp{0}" -f ($hp -replace '\.', ''))
            if ($hp -eq "0.2") { $tag = "hp020" }
            if ($hp -eq "0.5") { $tag = "hp050" }
            if ($hp -eq "1.0") { $tag = "hp100" }
            $outDir = "workspace/audio_raw_economy/_local_gpu_weekly/$tag"
            Invoke-PyStep -Id ("musicgen_chain_$tag") -Phase "local_cuda" -PyArgs @(
                "scripts/run_dynamic_bgm_melody_chain_v1.py",
                "--seed-json", "data/audio/seeds/tension_sasang_01.example.json",
                "--hp-pct", $hp,
                "--sasang", "soyang",
                "--output-dir", $outDir,
                "--placeholder-seconds", "8",
                "--demo-report-json", "$outDir/_point_demo.json"
            )
        }
        $demoHp100 = Join-Path $resolvedRoot "workspace/audio_raw_economy/_local_gpu_weekly/hp100/_point_demo.json"
        if (Test-Path -LiteralPath $demoHp100) {
            Copy-Item -LiteralPath $demoHp100 `
                -Destination (Join-Path $resolvedRoot "docs/final/artifacts/dynamic_bgm_melody_chain_demo_v1_latest.json") `
                -Force
        }
        Invoke-PyStep -Id "hp_sweep_post_gen" -Phase "local_cuda" -PyArgs @(
            "scripts/run_dynamic_bgm_hp_sweep_v1.py", "--conditioning-only"
        )
        Invoke-PyStep -Id "stage_audio_hook_samples_post_gen" -Phase "cpu" -PyArgs @(
            "scripts/stage_track_c_audio_hook_samples_for_counsel_v1.py"
        )
        if (-not $SkipCounselZip) {
            Invoke-PyStep -Id "counsel_export_manifest_post_gen" -Phase "cpu" -PyArgs @(
                "scripts/build_track_c_b2b_counsel_export_manifest_v1.py", "--fail-if-missing"
            )
            Invoke-PyStep -Id "counsel_export_zip_post_gen" -Phase "cpu" -PyArgs @(
                "scripts/build_track_c_b2b_counsel_zip_pack_v1.py"
            )
        }
    }

    if ($IncludeMusicGenLoop32Smoke) {
        Invoke-PsStep -Id "musicgen_loop32_smoke" -Phase "local_cuda" `
            -ScriptRel "scripts\Run-MusicGenLoop32Smoke_v1.ps1" `
            -ExtraArgs @("-WorkspaceRoot", $resolvedRoot)
    }

    if ($IncludeMediaThinSliceBake) {
        Invoke-PyStep -Id "lens_btrack_lut_matrix" -Phase "cpu" -PyArgs @(
            "scripts/build_lens_btrack_playback_lut_matrix_v1.py"
        )
        if ($IncludeAudioGenerate) {
            Invoke-PyStep -Id "lens_btrack_audio_loops_musicgen" -Phase "local_cuda" -PyArgs @(
                "scripts/build_lens_btrack_audio_loops_musicgen_v1.py",
                "--fallback-tone",
                "--seconds", "12"
            )
            Invoke-PyStep -Id "lens_btrack_audio_loudnorm" -Phase "cpu_ffmpeg" -PyArgs @(
                "scripts/normalize_lens_btrack_audio_loudness_v1.py"
            )
            Invoke-PyStep -Id "lens_btrack_lut_gates_sync" -Phase "cpu" -PyArgs @(
                "scripts/apply_lens_btrack_lut_gates_from_bake_v1.py"
            )
        } else {
            Invoke-PyStep -Id "lens_btrack_audio_loops_bake" -Phase "cpu" -PyArgs @(
                "scripts/build_lens_btrack_audio_loops_v1.py"
            )
        }
        Invoke-PyStep -Id "lens_btrack_video_loops_bake" -Phase "cpu_ffmpeg" -PyArgs @(
            "scripts/build_lens_btrack_video_loops_v1.py",
            "--renderer", "animated"
        )
        Invoke-PyStep -Id "lens_btrack_video_mp4_fallback" -Phase "cpu_ffmpeg" -PyArgs @(
            "scripts/build_lens_btrack_video_mp4_fallback_v1.py"
        )
        Invoke-PyStep -Id "lens_media_observability_build" -Phase "cpu" -PyArgs @(
            "scripts/build_showroom_lens_media_observability_v1.py",
            "--from-macro-slice"
        )
        if ($env:MKM_LENS_STABLE_AUDIO_AB -eq '1') {
            Invoke-PyStep -Id "lens_stable_audio_prereqs" -Phase "cpu" -PyArgs @(
                "scripts/check_lens_stable_audio_prereqs_v1.py", "--probe-model"
            )
            Invoke-PyStep -Id "lens_audio_generator_ab_smoke" -Phase "local_cuda" -PyArgs @(
                "scripts/run_lens_btrack_audio_generator_ab_smoke_v1.py",
                "--skip-generate", "--stable-steps", "50"
            )
        }
        Invoke-PyStep -Id "stage_media_hook_samples" -Phase "cpu" -PyArgs @(
            "scripts/stage_track_c_audio_hook_samples_for_counsel_v1.py"
        )
    }

    if ($IncludeKaggleLocalPrep) {
        Invoke-PsStep -Id "kaggle_nemotron_local_prep" -Phase "kaggle_cpu" `
            -ScriptRel "scripts\Invoke-KaggleNemotronTrainOnKaggle_v1.ps1"
    }

    if ($IncludeGpuRecommendedBundle) {
        Invoke-PsStep -Id "gpu_recommended_bundle" -Phase "local_cuda_light" `
            -ScriptRel "scripts\Run-MkmGpuRecommendedBundle_v1.ps1"
    }
}

$allOk = ($steps | Where-Object { -not $_.ok }).Count -eq 0
$sweepPath = Join-Path $resolvedRoot "docs\final\artifacts\dynamic_bgm_hp_sweep_v1_latest.json"
$sweepSummary = $null
if (Test-Path -LiteralPath $sweepPath) {
    $sw = Get-Content -LiteralPath $sweepPath -Raw | ConvertFrom-Json
    $sweepSummary = @{
        gate_pass = $sw.summary.gate_pass
        gate_fail = $sw.summary.gate_fail
        points    = $sw.summary.points
    }
}

$azurePath = Join-Path $resolvedRoot "reports\azure_support_ticket_status_latest.json"
$azureStatus = $null
if (Test-Path -LiteralPath $azurePath) {
    $az = Get-Content -LiteralPath $azurePath -Raw | ConvertFrom-Json
    $azureStatus = @{
        ticket_status = $az.status
        ncas_t4_limit = $az.ncas_t4_limit_eastus2
        stance        = "HOLD_until_quota_gt_0"
    }
}

$doc = [ordered]@{
    schema            = "local_gpu_weekly_routine_v1"
    generated_at_utc  = $started
    finished_at_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hypothesis_class  = "HYPO"
    track_wall        = "B_track_research_only"
    workspace_root    = $resolvedRoot
    plan              = $plan
    ok                = $allOk
    steps             = @($steps)
    sweep_summary     = $sweepSummary
    azure             = $azureStatus
    gpu_policy        = "docs/final/artifacts/nvidia_gpu_credit_lane_policy_v1.json"
    boundary_ack      = "Local RTX + Kaggle gate check only; Azure VM provision blocked until quota>0."
}

$outDir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
($doc | ConvertTo-Json -Depth 6) + "`n" | Set-Content -LiteralPath $OutJson -Encoding utf8

Write-Host ""
Write-Host ("local_gpu_weekly_routine: ok={0} report={1}" -f $allOk, $OutJson) -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })
exit $(if ($allOk) { 0 } else { 1 })
