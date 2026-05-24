#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly B-track auto-sweep (09:45) + learning bundle (10:15) via schtasks.exe.

.DESCRIPTION
  Uses schtasks.exe (same as GeneralProphecy tasks). Run from **elevated** PowerShell if Access denied.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-MkmBtrackProphecyLearningTasks_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SweepAt = "09:45",
    [string]$LearningAt = "10:15",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$sweepTask = "MKM-BTrack-RecommendedEval-AutoSweep-Weekly"
$learnTask = "MKM-BTrack-Prophecy-Weekly-Learning"
$sweepRunner = Join-Path $WorkspaceRoot "scripts\Run-BtrackRecommendedEvalAutoSweep_v1.ps1"
$learnRunner = Join-Path $WorkspaceRoot "scripts\Invoke-MkmBtrackProphecyWeeklyLearning_v1.ps1"

if ($Remove) {
    foreach ($tn in @($sweepTask, $learnTask)) {
        schtasks.exe /Delete /TN $tn /F 2>$null | Out-Null
        Write-Host "[REMOVED] $tn" -ForegroundColor Yellow
    }
    exit 0
}

foreach ($p in @($sweepRunner, $learnRunner)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing: $p" }
}

function Register-WeeklySchTask {
    param(
        [string]$TaskName,
        [string]$At,
        [string]$ArgLine
    )
    $tr = "powershell.exe $ArgLine"
    schtasks.exe /Create /TN $TaskName /SC WEEKLY /D SUN /ST $At /TR $tr /F 2>&1 | ForEach-Object { $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "schtasks /Create failed for $TaskName (exit=$LASTEXITCODE). Run this script as Administrator."
    }
    $q = schtasks.exe /Query /TN $TaskName /V /FO LIST 2>&1 | Out-String
    Write-Host "[DONE] $TaskName @ $At" -ForegroundColor Green
    Write-Host $q
}

$sweepArg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$sweepRunner`" -WorkspaceRoot `"$WorkspaceRoot`""
$learnArg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$learnRunner`" -WorkspaceRoot `"$WorkspaceRoot`" -SkipAutoSweep"

Register-WeeklySchTask -TaskName $sweepTask -At $SweepAt -ArgLine $sweepArg
Register-WeeklySchTask -TaskName $learnTask -At $LearningAt -ArgLine $learnArg

Write-Host ""
Write-Host "Sunday chain: $SweepAt sweep -> $LearningAt promote+eval+watchdog+registry seed" -ForegroundColor Cyan
