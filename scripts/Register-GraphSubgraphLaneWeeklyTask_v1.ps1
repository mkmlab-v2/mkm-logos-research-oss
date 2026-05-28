<#
.SYNOPSIS
  Register weekly Scheduled Task for Graph subgraph lane (Logos replay + Pet PoC + pytest).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_GraphSubgraph_LaneWeekly",
    [string]$WeeklyAt = "09:10",
    [string]$DayOfWeek = "Sunday"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    "C:\workspace"
}
$runner = Join-Path $workspaceRoot "scripts\Run-GraphSubgraphLaneWeekly_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WeeklyAt -split ':'
if ($parts.Count -lt 2) {
    throw "WeeklyAt must be HH:mm, got: $WeeklyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$atToday = Get-Date -Hour $hour -Minute $minute -Second 0

$runnerArgs = @(
    "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`""
)
$arg = ($runnerArgs -join " ")

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $atToday
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "B-track Graph subgraph lane: Logos q01-q12 replay + Pet observation PoC ([HYPO], NON_GATING)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName weekly on $DayOfWeek at $WeeklyAt"
Write-Host "Runner: $runner"
Write-Host "Verify: scripts\Verify-GraphSubgraphLaneWeeklyTask_v1.ps1"
