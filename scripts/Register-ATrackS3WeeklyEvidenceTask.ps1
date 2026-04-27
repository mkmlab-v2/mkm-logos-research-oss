param(
    [switch]$Remove,
    [string]$TaskName = "MKM_ATrack_S3_Weekly_Evidence",
    [string]$WeeklyDay = "Sunday",
    [string]$WeeklyAt = "07:30"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_a_track_s3_weekly_evidence_rollup_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task (if existed): $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WeeklyAt -split ":"
if ($parts.Count -lt 2) {
    throw "WeeklyAt must be HH:mm (e.g. 07:30), got: $WeeklyAt"
}
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0

$dayMap = @{
    "Sunday" = [System.DayOfWeek]::Sunday
    "Monday" = [System.DayOfWeek]::Monday
    "Tuesday" = [System.DayOfWeek]::Tuesday
    "Wednesday" = [System.DayOfWeek]::Wednesday
    "Thursday" = [System.DayOfWeek]::Thursday
    "Friday" = [System.DayOfWeek]::Friday
    "Saturday" = [System.DayOfWeek]::Saturday
}
if (-not $dayMap.ContainsKey($WeeklyDay)) {
    throw "WeeklyDay must be one of: Sunday..Saturday"
}

$runCmd = "Set-Location -LiteralPath '$workspaceRoot'; py '$runner'"
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"$runCmd`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $dayMap[$WeeklyDay] -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Weekly Track A S3 evidence rollup and checklist refresh." -Force | Out-Null

Write-Host "Registered: $TaskName ($WeeklyDay $WeeklyAt)"
Write-Host "Runner: $runner"
