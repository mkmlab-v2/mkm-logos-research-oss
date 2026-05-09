[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [ValidateRange(1, 500)]
    [int]$Iterations = 25,
    [ValidateRange(0, 600)]
    [int]$SleepSeconds = 5,
    [switch]$SkipOrchestratorRun,
    [switch]$EnableAutoDemotion,
    [switch]$EnableAutoPromotion,
    [ValidateRange(1, 20)]
    [int]$AutoPromotionMinGoStreak = 3,
    [switch]$RebuildGoPlusReport,
    [ValidateRange(0, 1440)]
    [int]$ReportWindowMinutes = 0,
    [ValidateRange(0, 10000)]
    [int]$ReportTailSamples = 0,
    [switch]$ReportTailMatchIterations,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\run_mkm_orchestrator_go_stability_cycle_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner: $runner"
}

$started = Get-Date
Write-Output "accelerated_burnin_v1: iterations=$Iterations sleep_sec=$SleepSeconds dry_run=$DryRun"

if ($DryRun) {
    Write-Output "dry_run: would run $Iterations cycles"
    exit 0
}

Push-Location $WorkspaceRoot
try {
    $failCount = 0
    for ($i = 1; $i -le $Iterations; $i++) {
        $cmdArgs = @{
            WorkspaceRoot       = $WorkspaceRoot
            SkipOrchestratorRun = [bool]$SkipOrchestratorRun
        }
        if ($EnableAutoDemotion) {
            $cmdArgs.EnableAutoDemotion = $true
        }
        if ($EnableAutoPromotion) {
            $cmdArgs.EnableAutoPromotion = $true
            $cmdArgs.AutoPromotionMinGoStreak = $AutoPromotionMinGoStreak
        }
        & $runner @cmdArgs
        $exitCode = $LASTEXITCODE
        # Stability checker exits 1 when not GO-stable (WATCH/HOLD/down-transition) — expected during burn-in.
        # Treat only hard failures (>=2) as cycle failures.
        if ($exitCode -ge 2) {
            $failCount++
            Write-Warning "cycle $i exit $exitCode"
        }
        Write-Output "cycle $i/$Iterations exit=$exitCode"
        if ($i -lt $Iterations -and $SleepSeconds -gt 0) {
            Start-Sleep -Seconds $SleepSeconds
        }
    }

    $elapsed = (Get-Date) - $started
    Write-Output "accelerated_burnin_v1: done elapsed_sec=$([math]::Round($elapsed.TotalSeconds,1)) failure_cycles=$failCount"

    if ($RebuildGoPlusReport) {
        $wm = $ReportWindowMinutes
        if ($wm -le 0) {
            $wm = [math]::Max(5, [math]::Ceiling($elapsed.TotalMinutes) + 2)
        }
        $ts = 0
        if ($ReportTailMatchIterations) {
            $ts = $Iterations
        }
        elseif ($ReportTailSamples -gt 0) {
            $ts = $ReportTailSamples
        }
        $reportPy = Join-Path $WorkspaceRoot "scripts\build_mkm_conditional_go_plus_report_v2.py"
        if ($ts -gt 0) {
            & py $reportPy --window-minutes $wm --tail-samples $ts
        }
        else {
            & py $reportPy --window-minutes $wm
        }
        if ($LASTEXITCODE -ne 0) {
            throw "build_mkm_conditional_go_plus_report_v2.py failed"
        }
    }

    exit $(if ($failCount -gt 0) { 1 } else { 0 })
}
finally {
    Pop-Location
}
