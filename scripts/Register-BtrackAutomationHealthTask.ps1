param(
    [switch]$Remove,
    [string]$TaskName = "MKM_BTrack_Automation_Health_Daily",
    [string]$DailyAt = "01:20",
    [switch]$IncludeAlert,
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\build_btrack_automation_health_snapshot_v1.py"
$alerter = Join-Path $workspaceRoot "scripts\alert_btrack_automation_health_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task (if existed): $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if ($IncludeAlert -and -not (Test-Path -LiteralPath $alerter)) {
    throw "Alerter not found: $alerter"
}

$parts = $DailyAt -split ":"
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 01:20), got: $DailyAt"
}
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0

$runCmd = "Set-Location -LiteralPath '$workspaceRoot'; py '$runner'"
if ($IncludeAlert) {
    $runCmd += "; py '$alerter' --always-log"
}
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"$runCmd`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Daily B-track automation health snapshot." -Force | Out-Null

Write-Host "Registered: $TaskName (Daily $DailyAt)"
Write-Host "Runner: $runner"
if ($IncludeAlert) {
    Write-Host "Alerter: $alerter"
}
