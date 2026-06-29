# Register 5-minute poll: new JSONL in data/wtt/intake -> Invoke-WttPilotIntakeAuto.
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_WttPilot_IntakeDropWatch",
    [int]$IntervalMinutes = 5
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$watchPs1 = Join-Path $WorkspaceRoot "scripts\Invoke-WttPilotIntakeDropWatch_v1.ps1"
$log = Join-Path $WorkspaceRoot "reports\wtt_pilot_intake_drop_watch_task.log"

if (-not (Test-Path -LiteralPath $watchPs1)) {
    throw "Missing: $watchPs1"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$cmdArgs = "/c cd /d `"$WorkspaceRoot`" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$watchPs1`" -WorkspaceRoot `"$WorkspaceRoot`" >> `"$log`" 2>&1"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$start = (Get-Date).AddMinutes(1)
$trigger = New-ScheduledTaskTrigger -Once -At $start `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration ([TimeSpan]::FromDays(3650))
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered: $TaskName" -ForegroundColor Green
Write-Host "  Poll every $IntervalMinutes min | log: $log"
Write-Host "  Drop: data/wtt/intake/<tenant-slug>.jsonl (customer_provided, >=20 sessions)"
Write-Host "  Unregister: -Remove on Register-WttPilotIntakeDropWatchTask.ps1"
exit 0
