<#
.SYNOPSIS
  Regenerates Track B weekly artifacts: domain pairs, Jaccard + cosine_tokens evals,
  by_domain aggregate, OOV sweep, action gate, determinism, selective-state sims, weekly gate recheck.
  Optional: SSM vs TF toy microbench (CPU/CUDA).

.NOTES
  Research lane only. Does not touch compression Genesis pipelines or live trading.
  Run from repo root:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-TrackBWeeklyRefresh.ps1
#>
[CmdletBinding()]
param(
    [switch] $SkipSsmSmoke,
    [switch] $SkipCosine,
    [switch] $IncludeExtendedStressGrid,
    [switch] $IncludeExtendedStressB2,
    [string] $OovRatios = "0.0,0.05,0.1,0.15,0.2,0.25,0.3"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Step([string]$Label, [string[]]$PyArgs) {
    Write-Host "==> $Label" -ForegroundColor Cyan
    $p = Start-Process -FilePath "py" -ArgumentList $PyArgs -WorkingDirectory $root -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) { throw "py failed (exit $($p.ExitCode)): $Label" }
}

Invoke-Step "generate_trackb_domain_pairs" @("scripts/generate_trackb_domain_pairs.py")

foreach ($pair in @(
    @{ domain = "medical"; file = "trackb_semantic_eval_pairs_medical_v1.jsonl" },
    @{ domain = "finance"; file = "trackb_semantic_eval_pairs_finance_v1.jsonl" },
    @{ domain = "policy";  file = "trackb_semantic_eval_pairs_policy_v1.jsonl" }
)) {
    Invoke-Step "semantic_eval_jaccard_$($pair.domain)" @(
        "scripts/track_b_semantic_eval.py",
        "--pairs", "docs/final/artifacts/$($pair.file)",
        "--out", "docs/final/artifacts/trackb_semantic_eval_$($pair.domain)_latest.json"
    )
}

Invoke-Step "build_trackb_semantic_eval_by_domain" @("scripts/build_trackb_semantic_eval_by_domain.py")

if (-not $SkipCosine) {
    foreach ($pair in @(
        @{ domain = "medical"; file = "trackb_semantic_eval_pairs_medical_v1.jsonl" },
        @{ domain = "finance"; file = "trackb_semantic_eval_pairs_finance_v1.jsonl" },
        @{ domain = "policy";  file = "trackb_semantic_eval_pairs_policy_v1.jsonl" }
    )) {
        Invoke-Step "semantic_eval_cosine_$($pair.domain)" @(
            "scripts/track_b_semantic_eval.py",
            "--pairs", "docs/final/artifacts/$($pair.file)",
            "--semantic-metric", "cosine_tokens",
            "--out", "docs/final/artifacts/trackb_semantic_eval_$($pair.domain)_cosine_tokens_latest.json"
        )
    }
}

Invoke-Step "run_trackb_oov_sweep" @(
    "scripts/run_trackb_oov_sweep.py",
    "--oov-ratios", $OovRatios
)

Invoke-Step "run_trackb_action_gate_pilot" @("scripts/run_trackb_action_gate_pilot.py")
Invoke-Step "run_trackb_determinism_repeatcheck" @("scripts/run_trackb_determinism_repeatcheck.py")

Invoke-Step "selective_state_sim_default" @("scripts/run_trackb_selective_state_sim.py")
Invoke-Step "selective_state_sim_triggercase" @(
    "scripts/run_trackb_selective_state_sim.py",
    "--out", "docs/final/artifacts/trackb_action_layer_selective_state_sim_triggercase_latest.json"
)

if (-not $SkipSsmSmoke) {
    Invoke-Step "trackb_ssm_vs_tf_bench_cpu" @(
        "scripts/trackb_ssm_vs_tf_bench.py", "--run-smoke", "--device", "cpu", "--repeats", "2"
    )
    Invoke-Step "trackb_ssm_vs_tf_bench_cuda" @(
        "scripts/trackb_ssm_vs_tf_bench.py",
        "--run-smoke", "--device", "cuda",
        "--micro-out", "docs/final/artifacts/trackb_ssm_vs_tf_bench_micro_cuda_latest.json",
        "--repeats", "2"
    )
}

Invoke-Step "run_trackb_weekly_gate_recheck" @("scripts/run_trackb_weekly_gate_recheck.py")
Invoke-Step "build_trackb_quaternion_top_combo_ranking" @("scripts/build_trackb_quaternion_top_combo_ranking.py")
Invoke-Step "build_trackb_top_combo_fixed_set" @("scripts/build_trackb_top_combo_fixed_set.py")
Invoke-Step "run_trackb_top_combo_fixed_set_replay" @("scripts/run_trackb_top_combo_fixed_set_replay.py")
Invoke-Step "run_trackb_top_combo_stress_grid" @("scripts/run_trackb_top_combo_stress_grid.py")

if ($IncludeExtendedStressGrid) {
    # Bounded split mode for stable weekly completion.
    # 1) Pin to robust exact candidate only.
    Invoke-Step "build_trackb_top_combo_fixed_set_exact_robust_only" @(
        "scripts/build_trackb_top_combo_fixed_set.py",
        "--top-n", "1",
        "--artifact-contains", "exact_guarded_robust",
        "--out", "docs/final/artifacts/trackb_quaternion_top_combo_fixed_set_exact_robust_only_latest.json"
    )
    # 2) Split stress into smaller chunks to avoid monolithic long-running stalls.
    Invoke-Step "run_trackb_top_combo_stress_grid_extended_split_a" @(
        "scripts/run_trackb_top_combo_stress_grid.py",
        "--fixed-set", "docs/final/artifacts/trackb_quaternion_top_combo_fixed_set_exact_robust_only_latest.json",
        "--lengths", "20,24,32",
        "--oov-ratios", "0.1,0.3,0.5",
        "--samples-per-cell-cap", "240",
        "--out", "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_exact_robust_split_a_latest.json"
    )
    Invoke-Step "run_trackb_top_combo_stress_grid_extended_split_b1" @(
        "scripts/run_trackb_top_combo_stress_grid.py",
        "--fixed-set", "docs/final/artifacts/trackb_quaternion_top_combo_fixed_set_exact_robust_only_latest.json",
        "--lengths", "40,48",
        "--oov-ratios", "0.1,0.3,0.5",
        "--samples-per-cell-cap", "240",
        "--out", "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_exact_robust_split_b1_latest.json"
    )
    if ($IncludeExtendedStressB2) {
        Invoke-Step "run_trackb_top_combo_stress_grid_extended_split_b2" @(
            "scripts/run_trackb_top_combo_stress_grid.py",
            "--fixed-set", "docs/final/artifacts/trackb_quaternion_top_combo_fixed_set_exact_robust_only_latest.json",
            "--lengths", "64",
            "--oov-ratios", "0.1,0.3,0.5",
            "--samples-per-cell-cap", "240",
            "--out", "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_exact_robust_split_b2_latest.json"
        )
    }
}

Write-Host "Track B weekly refresh completed. See docs/final/artifacts/trackb_weekly_gate_recheck_latest.json" -ForegroundColor Green
