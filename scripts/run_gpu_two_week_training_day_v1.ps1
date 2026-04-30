param(
    [int]$DayIndex = 1
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$planPath = "docs/final/artifacts/gpu_two_week_training_plan_v1_latest.json"
if (-not (Test-Path -LiteralPath $planPath)) {
    throw "Training plan not found: $planPath"
}

$plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
$entry = $plan.schedule | Where-Object { [int]$_.day_index -eq $DayIndex } | Select-Object -First 1
if ($null -eq $entry) {
    throw "No schedule entry for day_index=$DayIndex"
}

Write-Host ("[training] day={0} focus={1}" -f $entry.day_index, $entry.focus)

switch ([string]$entry.focus) {
    "gpu_shadow_calibration" {
        py "scripts/build_gpu_shadow_runtime_score_v1.py"
    }
    "regime_threshold_retune" {
        py "scripts/build_gpu_universal_precursor_resweep_v1.py"
    }
    "rollback_drill_scoring" {
        py "scripts/run_prophecy_live_rollback_drill_v1.py"
    }
    "weekly_review" {
        py "scripts/build_live_gpu_unified_status_dashboard_v1.py"
    }
    default {
        throw "Unknown focus: $($entry.focus)"
    }
}

Write-Host "DONE: gpu two-week training day run complete."
