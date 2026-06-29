#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Scheduled Task: Magic Orb design readiness (Playwright + SSOT merge).

.PARAMETER SundayAt
  Local time HH:mm (default: 10:25 — after deployment axis isolation 10:10).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_MagicOrb_DesignReadiness_Weekly",
    [string]$SundayAt = "10:25"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$runner = Join-Path $workspaceRoot "scripts\Invoke-MkmMagicOrbDesignReadinessWeeklyRoutine_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = @"
Weekly Magic Orb design/UX readiness: Playwright screenshot + engineering probe merge.
[HYPO] B-track — consumer_ready requires commander visual; no Track A promotion.
"@.Trim()

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt)"
Write-Host "Verify: powershell -File scripts\Verify-MkmMagicOrbDesignReadinessWeeklyScheduledTask_v1.ps1"
