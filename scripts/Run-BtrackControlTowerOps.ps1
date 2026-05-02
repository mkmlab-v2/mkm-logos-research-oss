param(
    [ValidateSet("weekly","autopush","brief","preflight")]
    [string]$Mode = "brief",
    [switch]$SkipPhase2,
    [switch]$DisableSignalLightRouting,
    [switch]$AutoApplyOnGoReady,
    [switch]$ApplyForce,
    [switch]$ApplyDryRun,
    [int]$MaxRuns = 5,
    [int]$CooldownSeconds = 60,
    [double]$AutopushMinAccuracyDelta = 0.0
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$weekly = Join-Path $workspaceRoot "scripts\Run-BtrackAutoScientistWeekly.ps1"
$autopush = Join-Path $workspaceRoot "scripts\Run-BtrackAutoScientistAutopush.ps1"
$brief = Join-Path $workspaceRoot "scripts\print_auto_scientist_ops_brief_v1.py"
$preflight = Join-Path $workspaceRoot "scripts\run_btrack_promotion_preflight_v1.py"
$rehearsal = Join-Path $workspaceRoot "scripts\build_btrack_rehearsal_receipt_v1.py"
$applyAtomic = Join-Path $workspaceRoot "scripts\Apply-BtrackPromotionAtomic.ps1"

Set-Location -LiteralPath $workspaceRoot

function Write-RehearsalReceipt([string]$ModeName, [int]$RunnerExitCode, [int]$NormalizedExitCode) {
    if (-not (Test-Path -LiteralPath $rehearsal)) { return }
    & py -u $rehearsal --trigger-mode $ModeName --runner-exit-code $RunnerExitCode --normalized-exit-code $NormalizedExitCode
}

function Invoke-AtomicApplyIfEnabled([int]$CurrentExitCode) {
    if ($CurrentExitCode -ne 0 -or -not $AutoApplyOnGoReady) { return $CurrentExitCode }
    if (-not (Test-Path -LiteralPath $applyAtomic)) {
        Write-Host "[control-tower-ops] auto-apply requested but apply script not found: $applyAtomic" -ForegroundColor Red
        return 1
    }
    $applyArgs = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$applyAtomic)
    if ($ApplyForce) { $applyArgs += "-Force" }
    if ($ApplyDryRun) { $applyArgs += "-DryRun" }
    & powershell @applyArgs | Out-Null
    return $LASTEXITCODE
}

switch ($Mode) {
    "weekly" {
        $args = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$weekly)
        if ($SkipPhase2) { $args += "-SkipPhase2" }
        if ($DisableSignalLightRouting) { $args += "-DisableSignalLightRouting" }
        & powershell @args
        $rc = $LASTEXITCODE
        $rc = Invoke-AtomicApplyIfEnabled -CurrentExitCode $rc
        Write-RehearsalReceipt -ModeName "weekly" -RunnerExitCode $rc -NormalizedExitCode $rc
        exit $rc
    }
    "autopush" {
        $args = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$autopush,"-MaxRuns","$MaxRuns","-CooldownSeconds","$CooldownSeconds","-MinAccuracyDelta","$AutopushMinAccuracyDelta")
        if ($SkipPhase2) { $args += "-SkipPhase2" }
        & powershell @args
        $runnerRc = $LASTEXITCODE
        $normalizedRc = $runnerRc
        # Normalize bounded campaign completion for schedulers.
        if ($runnerRc -eq 3) {
            Write-Host "[control-tower-ops] autopush returned 3 (max-runs bounded stop) -> normalized to 0." -ForegroundColor Yellow
            $normalizedRc = 0
        }
        $finalRc = Invoke-AtomicApplyIfEnabled -CurrentExitCode $normalizedRc
        Write-RehearsalReceipt -ModeName "autopush" -RunnerExitCode $runnerRc -NormalizedExitCode $finalRc
        exit $finalRc
    }
    "brief" {
        & py -u $brief
        exit $LASTEXITCODE
    }
    "preflight" {
        & py -u $preflight
        exit $LASTEXITCODE
    }
}
