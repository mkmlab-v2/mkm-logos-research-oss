# Chronos-Forward KOSPI baseline (reproducible entry point)
# Writes:
#   - Mode training   -> data/chronos_forward_training/training_result.json
#   - Mode holdout2026 -> data/chronos_forward_training/holdout_2026_result.json
#   - Mode both        -> training run, then holdout 2026 run
#
# Default period: tools/prophecy/chronos_forward_trainer.py ChronosForwardTrainer defaults.

param(
    [ValidateSet("training", "holdout2026", "both")]
    [string]$Mode = "both",
    [int]$SaveInterval = 50,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$workspace = "C:\workspace"
Set-Location $workspace

$vf = if ($Quiet) { "False" } else { "True" }

function Invoke-TrainingOnly {
    $cmd = "from tools.prophecy.chronos_forward_trainer import ChronosForwardTrainer; t=ChronosForwardTrainer(); t.run_training(save_interval=$SaveInterval, verbose=$vf)"
    py -c $cmd
    if ($LASTEXITCODE -ne 0) { throw "Chronos-Forward training baseline failed" }
}

function Invoke-Holdout2026 {
    $cmd = "from tools.prophecy.chronos_forward_trainer import ChronosForwardTrainer; t=ChronosForwardTrainer(); t.run_training(save_interval=$SaveInterval, verbose=$vf, holdout_year=2026)"
    py -c $cmd
    if ($LASTEXITCODE -ne 0) { throw "Chronos-Forward holdout 2026 baseline failed" }
}

switch ($Mode) {
    "training" {
        Write-Host "[chronos-baseline] Mode=training -> training_result.json"
        Invoke-TrainingOnly
    }
    "holdout2026" {
        Write-Host "[chronos-baseline] Mode=holdout2026 -> holdout_2026_result.json"
        Invoke-Holdout2026
    }
    "both" {
        Write-Host "[chronos-baseline] Mode=both: training then holdout2026"
        Invoke-TrainingOnly
        Invoke-Holdout2026
    }
}

Write-Host "[chronos-baseline] OK"
exit 0
