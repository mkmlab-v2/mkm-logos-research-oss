param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-Logos-PureReal-WeeklySnapshot",
    [string]$At = "08:00",
    [ValidateSet("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")]
    [string]$DayOfWeek = "Sunday",
    [string]$SnapshotLabel = "weekly_baseline"
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Run-LogosPureRealWeeklySnapshot-v1.ps1"
if (-not (Test-Path $runner)) {
  throw "Runner script not found: $runner"
}

$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -SnapshotLabel `"$SnapshotLabel`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $DayOfWeek -At $At
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null

Write-Output "{`"ok`":true,`"task`":`"$TaskName`",`"day_of_week`":`"$DayOfWeek`",`"at`":`"$At`"}"

