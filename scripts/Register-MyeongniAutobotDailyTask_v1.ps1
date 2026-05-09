<#
.SYNOPSIS
  Register daily one-shot myeongni autobot task.
#>
param(
    [switch]$Remove,
    [switch]$WhatIf,
    [string]$TaskName = "MKM_MyeongniAutobot_Daily",
    [string]$DailyAt = "06:20",
    [string]$Name = "commander",
    [int]$Year = 1973,
    [int]$Month = 12,
    [int]$Day = 10,
    [int]$Hour = 4,
    [int]$Minute = 30,
    [int]$Second = 0,
    [string]$IanaTz = "Asia/Seoul",
    [switch]$IsMale,
    [string]$UserPrompt = "오늘 흐름 자동 요약",
    [int]$AnnualStartYear = 2026,
    [int]$AnnualYears = 3,
    [int]$MonthlyMonthsPerYear = 3
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-MyeongniAutobotOnce_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "Runner not found: $runner" }

if ($Remove) {
    if ($WhatIf) { Write-Host "[WhatIf] remove $TaskName"; exit 0 }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed: $TaskName"
    exit 0
}

$parts = $DailyAt -split ':'
$atToday = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0

$runnerArgs = @(
    "-NoProfile","-WindowStyle","Hidden","-ExecutionPolicy","Bypass",
    "-File","`"$runner`"",
    "-Name",$Name,
    "-Year","$Year","-Month","$Month","-Day","$Day","-Hour","$Hour","-Minute","$Minute","-Second","$Second",
    "-IanaTz",$IanaTz,
    "-UserPrompt","`"$UserPrompt`"",
    "-AnnualStartYear","$AnnualStartYear","-AnnualYears","$AnnualYears","-MonthlyMonthsPerYear","$MonthlyMonthsPerYear"
)
if ($IsMale) { $runnerArgs += "-IsMale" }
$argLine = $runnerArgs -join " "

if ($WhatIf) {
    Write-Host "[WhatIf] Register $TaskName at $DailyAt"
    Write-Host "[WhatIf] powershell.exe $argLine"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Daily one-shot myeongni autobot response generation" -Force | Out-Null
Write-Host "Registered: $TaskName"
Write-Host "Argument: $argLine"
exit 0

