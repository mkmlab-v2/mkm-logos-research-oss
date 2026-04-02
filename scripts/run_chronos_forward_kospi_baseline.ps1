# Chronos-Forward KOSPI baseline (reproducible entry point)
# Writes:
#   - Mode training   -> data/chronos_forward_training/training_result.json
#   - Mode holdout2026 -> data/chronos_forward_training/holdout_2026_result.json
#   - Mode both        -> training run, then holdout 2026 run
#
# Default period: tools/prophecy/chronos_forward_trainer.py ChronosForwardTrainer defaults.
#
# Recommended: long runs — use -Detached so the job survives Cursor/agent terminal limits:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_chronos_forward_kospi_baseline.ps1 -Mode both -Detached

param(
    [ValidateSet("training", "holdout2026", "both")]
    [string]$Mode = "both",
    [int]$SaveInterval = 50,
    [ValidateSet("gpu", "cpu")]
    [string]$Compute = "gpu",
    [switch]$Quiet,
    [switch]$Detached
)

$ErrorActionPreference = "Stop"
$workspace = "C:\workspace"
$pyScript = Join-Path $workspace "scripts\run_chronos_forward_kospi_baseline.py"
Set-Location $workspace

if ($Detached) {
    $self = Join-Path $PSScriptRoot "run_chronos_forward_kospi_baseline.ps1"
    $childArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $self,
        "-Mode", $Mode, "-SaveInterval", $SaveInterval, "-Compute", $Compute
    )
    if ($Quiet) { $childArgs += "-Quiet" }
    $exe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell" }
    Start-Process -FilePath $exe -ArgumentList $childArgs -WorkingDirectory $workspace
    Write-Host "[chronos-baseline] Detached pwsh started (Mode=$Mode). Watch: data/chronos_forward_training/training_result.json / holdout_2026_result.json"
    exit 0
}

$pyArgs = @($pyScript, "--mode", $Mode, "--save-interval", "$SaveInterval")
if ($Compute -eq "gpu") {
    $pyArgs += "--use-gpu"
} else {
    $pyArgs += "--no-use-gpu"
}
if ($Quiet) { $pyArgs += "--quiet" }

Write-Host "[chronos-baseline] Mode=$Mode Compute=$Compute -> py $($pyArgs -join ' ')"

py @pyArgs
if ($LASTEXITCODE -ne 0) { throw "Chronos-Forward KOSPI baseline failed (exit $LASTEXITCODE)" }

Write-Host "[chronos-baseline] OK"
exit 0
