#Requires -Version 5.1

<#

.SYNOPSIS

  Morning NASDAQ settlement for prior US session (default 07:50 KST).

#>

param(

    [string]$WorkspaceRoot = "C:\workspace",

    [string]$At = "07:50",

    [string]$TaskName = "MKM-Commander-Morning-Nasdaq-Settlement",

    [switch]$Remove

)



$ErrorActionPreference = "Stop"



if ($Remove) {

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null

    Write-Host "[REMOVED] $TaskName" -ForegroundColor Yellow

    exit 0

}



$loader = @'

Set-Location -LiteralPath '__WORKSPACE__'

py scripts/fetch_nasdaq_yfinance_csv.py

if ($LASTEXITCODE -ne 0) { Write-Warning "nasdaq fetch exit $LASTEXITCODE" }

py scripts/score_commander_morning_nasdaq_settlement_v1.py

exit $LASTEXITCODE

'@

$loader = $loader.Replace('__WORKSPACE__', $WorkspaceRoot.Replace("'", "''"))

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"$loader`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $At

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew -Hidden

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Score NASDAQ pending predictions from prior morning archive [HYPO]." -Force | Out-Null

$i = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host "[DONE] $TaskName at $At Next=$($i.NextRunTime)" -ForegroundColor Green

