#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily MKM AutonomousPatrol (자율점검) Windows scheduled task.

.DESCRIPTION
  Solo SSOT: task must be listed under mkm_scheduler_solo_core_stack_v1 allowed tiers
  before Ready (register_task_policy_v1). Default register = Disabled unless listed
  or -StartReady with membership (fail-closed).

.PARAMETER Remove
  Unregister the task.

.PARAMETER StartReady
  Enable Ready only if task is in solo core stack SSOT (fail-closed otherwise).
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_AutonomousPatrol_Daily",
    [string]$AtLocalTime = "07:30",
    [switch]$StartReady
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-MkmAutonomousPatrol_v1.ps1"
$log = Join-Path $WorkspaceRoot "reports\mkm_autonomous_patrol_daily.log"
$memberHelper = Join-Path $WorkspaceRoot "scripts\Test-MkmSoloCoreStackTaskMembership_v1.ps1"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$cmdArgs = @(
    "/c cd /d `"$WorkspaceRoot`" &&",
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`" -ContinueOnFail >> `"$log`" 2>&1"
) -join " "

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $AtLocalTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Disable-ScheduledTask -TaskName $TaskName | Out-Null
$stateNote = "Disabled"

$membership = & $memberHelper -TaskName $TaskName -WorkspaceRoot $WorkspaceRoot -PassThru
if ($StartReady) {
    if (-not $membership.member) {
        throw ("FAIL-CLOSED: \\{0} not in solo SSOT tiers. Add to mkm_scheduler_solo_core_stack_v1.json before -StartReady. Keeping Disabled." -f $TaskName)
    }
    Enable-ScheduledTask -TaskName $TaskName | Out-Null
    $stateNote = "Ready"
}
elseif ($membership.member) {
    Enable-ScheduledTask -TaskName $TaskName | Out-Null
    $stateNote = "Ready (ssot_listed)"
}
else {
    Write-Warning "\\$TaskName not in solo SSOT. Registered Disabled — add tier then re-run with -StartReady."
}

Write-Host "Registered: $TaskName state=$stateNote" -ForegroundColor Green
Write-Host "  Daily at $AtLocalTime (local)"
Write-Host "  Log: $log"
Write-Host "  Solo band: powershell -File scripts\Invoke-MkmSchedulerSoloCoreStackAudit_v1.ps1 -EnforceSoloBand"
