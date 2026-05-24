#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly Scheduled Task: Dual-KPI frozen vs per-date panel compare (observability only).

.DESCRIPTION
  Runs scripts/Invoke-FrozenVsPerDatePanelCompare_v1.ps1 (no --RunScoredEval by default).
  Default Sunday 09:50 — after RecommendedEval AutoSweep (09:45).
  B-track [HYPO]; does not change Track A headline artifacts.

.PARAMETER Remove
  Unregister the task.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-FrozenVsPerDatePanelCompareWeeklyTask_v1.ps1
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-BTrack-DualKpi-PanelCompare-Weekly",
    [string]$SundayAt = "09:50",
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$MinTrainRows = 3,
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Invoke-FrozenVsPerDatePanelCompare_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SundayAt must be HH:mm, got: $SundayAt"
}
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -MinTrainRows $MinTrainRows"
$tr = "powershell.exe $argLine"
schtasks.exe /Create /TN $TaskName /SC WEEKLY /D SUN /ST $SundayAt /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] schtasks failed exit=$LASTEXITCODE" -ForegroundColor Yellow
    exit $LASTEXITCODE
}
Write-Host "[DONE] Registered: $TaskName at Sunday $SundayAt"
Write-Host "  Runner: $runner"
