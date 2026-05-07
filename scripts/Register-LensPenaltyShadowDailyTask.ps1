<#
.SYNOPSIS
  Register/remove daily task for lens penalty shadow chain.
#>
param(
    [switch]$Remove,
    [switch]$WhatIf,
    [string]$TaskName = "MKM_LensPenaltyShadow_Daily",
    [string]$DailyAt = "06:35"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-LensPenaltyShadowDaily_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "Runner not found: $runner" }

if ($Remove) {
    if ($WhatIf) {
        Write-Host "[WhatIf] Unregister-ScheduledTask -TaskName $TaskName"
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) { throw "DailyAt must be HH:mm" }
$atToday = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0

$argLine = @(
    "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`""
) -join " "

if ($WhatIf) {
    Write-Host "[WhatIf] Register-ScheduledTask -TaskName $TaskName -DailyAt $DailyAt"
    Write-Host "[WhatIf] Action: powershell.exe $argLine"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Daily lens penalty shadow chain (size-only recommendation)." -Force | Out-Null
Write-Host "Registered scheduled task: $TaskName"
Write-Host "Argument: $argLine"
exit 0
