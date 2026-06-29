# Register daily patient intake internal PoC chain (smoke + gate + paste assistant).
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_PatientIntake_PoC_Daily",
    [string]$RunAt = "07:30"
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$runner = Join-Path $WorkspaceRoot "scripts\Invoke-PatientIntakeOpenPoC_v1.ps1"
$log = Join-Path $WorkspaceRoot "reports\patient_intake_poc_daily_task.log"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$cmdArgs = "/c cd /d `"$WorkspaceRoot`" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`" >> `"$log`" 2>&1"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered: $TaskName" -ForegroundColor Green
Write-Host "  Daily at $RunAt | log: $log"
Write-Host "  Unregister: -Remove on Register-PatientIntakePoCDailyTask_v1.ps1"
exit 0
