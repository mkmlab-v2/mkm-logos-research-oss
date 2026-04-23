# Register (or remove) a daily scheduled task for strict freeze drift gate.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\register_canon_singularity_strict_freeze_drift_task.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\register_canon_singularity_strict_freeze_drift_task.ps1 -DailyAt "07:10" -AppendHistory

param(
    [switch]$Remove,
    [string]$TaskName = "MKM_CanonSingularity_StrictFreezeDrift",
    [string]$DailyAt = "07:10",
    [switch]$AppendHistory,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$builder = Join-Path $workspaceRoot "scripts\core\build_canon_singularity_strict_freeze_drift_gate_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $builder)) {
    throw "Drift gate builder not found: $builder"
}

$runnerArgs = @($builder)
$runnerArgs += "--freeze-vfinal-json"
$runnerArgs += "docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.json"
if ($AppendHistory) {
    $runnerArgs += "--append-history"
}
$runnerArgString = ($runnerArgs -join " ")

if ($PrintOnly) {
    Write-Host "PrintOnly: no task registration performed."
    Write-Host "TaskName: $TaskName"
    Write-Host "DailyAt: $DailyAt"
    Write-Host "AppendHistory: $AppendHistory"
    Write-Host "RunnerArgs: $runnerArgString"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "py.exe" `
    -Argument $runnerArgString `
    -WorkingDirectory $workspaceRoot

$parts = $DailyAt -split ":"
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 07:10), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Run strict freeze drift gate daily. AppendHistory=$AppendHistory"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered task: $TaskName (daily at $DailyAt, user=$env:USERNAME)"
Write-Host "Builder: $builder"

