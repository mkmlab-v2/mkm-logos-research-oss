<#
.SYNOPSIS
  Register/remove scheduled task for B-Track 99% weekly rollup.

.NOTES
  Default profile runs lightweight weekly refresh first via Run-BTrack99PercentWeeklyRollup.ps1.
  Use -IncludeExtendedStress for heavy split stress runs.
#>
[CmdletBinding()]
param(
    [switch] $Remove,
    [switch] $DryRun,
    [string] $TaskName = "MKM_BTrack99_Weekly_Rollup",
    [string] $DayOfWeek = "Sunday",
    [string] $WeeklyAt = "02:10",
    [int] $WeeksInterval = 1,
    [int] $OperationalRuntimeBudgetMs = 300000,
    [switch] $IncludeExtendedStress,
    [switch] $IncludeExtendedStressB2
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-BTrack99PercentWeeklyRollup.ps1"

if ($Remove) {
    if ($DryRun) {
        Write-Host "[DryRun] Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task (if existed): $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WeeklyAt -split ":"
if ($parts.Count -lt 2) {
    throw "WeeklyAt must be HH:mm (e.g. 02:10), got: $WeeklyAt"
}
if ($WeeksInterval -lt 1) {
    throw "WeeksInterval must be >= 1, got: $WeeksInterval"
}
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0

$runnerArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`"",
    "-OperationalRuntimeBudgetMs", "$OperationalRuntimeBudgetMs"
)
if ($IncludeExtendedStress) {
    $runnerArgs += "-IncludeExtendedStress"
}
if ($IncludeExtendedStressB2) {
    $runnerArgs += "-WeeklyB2Included"
}
$argLine = ($runnerArgs -join " ")

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval $WeeksInterval -DaysOfWeek $DayOfWeek -At $at
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ($DryRun) {
    Write-Host "[DryRun] TaskName: $TaskName"
    Write-Host "[DryRun] Schedule: every $WeeksInterval week(s), $DayOfWeek $WeeklyAt"
    Write-Host "[DryRun] Command: powershell.exe $argLine"
    exit 0
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Weekly B-Track 99% rollup (research lane)." -Force | Out-Null

Write-Host "Registered: $TaskName (every $WeeksInterval week(s), $DayOfWeek $WeeklyAt)"
Write-Host "Runner: $runner"
Write-Host "OperationalRuntimeBudgetMs: $OperationalRuntimeBudgetMs"
if ($IncludeExtendedStress) {
    Write-Host "Mode: IncludeExtendedStress"
    if ($IncludeExtendedStressB2) {
        Write-Host "Mode: IncludeExtendedStressB2"
    }
}
