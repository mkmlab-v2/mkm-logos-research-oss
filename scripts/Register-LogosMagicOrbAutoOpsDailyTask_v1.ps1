#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily Logos Magic Orb quality lane auto ops (gold eval, closure, deploy, KV, probe).
  B-track [HYPO] — separate from MKM_Op30_MagicOrb_Envelope_Daily (O-P30 envelope/traffic).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Logos_MagicOrb_AutoOps_Daily",
    [string]$DailyAt = "08:15"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-LogosMagicOrbAutoOps_v1.ps1"

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
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -SkipRebuild" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Logos Magic Orb quality lane: gold eval, closure, CF deploy (token), KV, live probe. [HYPO] B-track."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName daily at $DailyAt (-SkipRebuild)"
Write-Host "Verify: powershell -File scripts\Verify-LogosMagicOrbAutoOpsDailyTask_v1.ps1"
Write-Host "Remove: powershell -File scripts\Register-LogosMagicOrbAutoOpsDailyTask_v1.ps1 -Remove"
