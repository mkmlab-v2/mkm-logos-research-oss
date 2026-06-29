<#
.SYNOPSIS
  Register weekly Scheduled Task for Layer-1-only Brier bench PoC chain.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-Layer1OnlyBrierBenchWeeklyTask_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-Layer1OnlyBrierBenchWeeklyTask_v1.ps1 -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-Layer1OnlyBrierBench-Weekly",
    [ValidateSet("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")]
    [string]$Day = "SUN",
    [string]$At = "08:30",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Invoke-Layer1OnlyBrierBenchWeekly_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner: $runner"
}

$parts = $At -split ':'
if ($parts.Count -lt 2) {
    throw "At must be HH:mm, got: $At"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$atTime = Get-Date -Hour $hour -Minute $minute -Second 0

$dayMap = @{
    MON = [System.DayOfWeek]::Monday
    TUE = [System.DayOfWeek]::Tuesday
    WED = [System.DayOfWeek]::Wednesday
    THU = [System.DayOfWeek]::Thursday
    FRI = [System.DayOfWeek]::Friday
    SAT = [System.DayOfWeek]::Saturday
    SUN = [System.DayOfWeek]::Sunday
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $dayMap[$Day] -At $atTime
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$desc = "Weekly Layer-1-only Brier bench PoC: live probe + resolution sync + eval (B-track wall)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] Registered: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime: $($info.NextRunTime)"
Write-Host "  Day/At: $Day $At"
Write-Host "  Runner: $runner"
