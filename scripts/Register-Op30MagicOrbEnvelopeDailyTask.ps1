<#
.SYNOPSIS
  Register daily O-P30 AutoRun (envelope + deploy + probe + CF + rollup).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Op30_MagicOrb_Envelope_Daily",
    [string]$DailyAt = "07:50"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-Op30AutoRun_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ':'
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$atToday = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 25)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "O-P30 magic orb: AutoRun daily (envelope, deploy, probe, CF, weekly rollup). [HYPO] B-track."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName daily at $DailyAt (Invoke-Op30AutoRun_v1.ps1)"
Write-Host "Remove: powershell -File scripts\Register-Op30MagicOrbEnvelopeDailyTask.ps1 -Remove"
