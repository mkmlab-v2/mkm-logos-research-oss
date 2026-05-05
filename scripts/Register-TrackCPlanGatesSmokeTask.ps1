<#

.SYNOPSIS

  Register (or remove) a weekly Scheduled Task: Track C plan gates smoke (orchestrator bundle + pytest).



.DESCRIPTION

  Default: Sunday 07:00 local. Runner: scripts\Invoke-TrackCPlanGatesSmoke.ps1

#>

param(

    [switch]$Remove,

    [string]$TaskName = "MKM_TrackC_PlanGatesSmoke",

    [string]$SundayAt = "07:00",

    [string]$WorkspaceRoot = "C:\workspace"

)



$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-TrackCPlanGatesSmoke.ps1"



if ($Remove) {

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

    Write-Host "Removed scheduled task: $TaskName"

    exit 0

}



if (-not (Test-Path -LiteralPath $runner)) {

    throw "Runner not found: $runner"

}



$parts = $SundayAt -split ':'

if ($parts.Count -lt 2) {

    throw "SundayAt must be HH:mm (e.g. 07:00), got: $SundayAt"

}

$hour = [int]$parts[0]

$minute = [int]$parts[1]

$at = Get-Date -Hour $hour -Minute $minute -Second 0



$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""



$action = New-ScheduledTaskAction -Execute "powershell.exe" `

    -Argument $argLine `

    -WorkingDirectory $WorkspaceRoot



$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at



$settings = New-ScheduledTaskSettingsSet `

    -StartWhenAvailable `

    -AllowStartIfOnBatteries `

    -DontStopIfGoingOnBatteries `

    -ExecutionTimeLimit (New-TimeSpan -Hours 2)



$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited



$description = "Weekly: verify_mkm_orchestrator_bundle + orchestrator pytest (Track C plan alignment smoke)."



Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `

    -Settings $settings -Principal $principal -Description $description -Force | Out-Null



Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"

Write-Host "Runner: $runner"

