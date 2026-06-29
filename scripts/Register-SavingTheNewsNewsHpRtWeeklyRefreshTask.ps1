param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_SavingTheNews_NewsHpRt_WeeklyRefresh",
    [string]$RunAt = "08:15",
    [ValidateSet("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")]
    [string]$DayOfWeek = "Sunday",
    [string]$NotBefore = "2026-06-08",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts\Invoke-SavingTheNewsNewsHpRtRefresh_v1.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$argLine = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"{0}"' -f $scriptPath),
    "-NotBefore", $NotBefore,
    "-SkipPytest"
) -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $RunAt
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$shortName = $TaskName.TrimStart("\")
if ((Get-ScheduledTask -TaskName $shortName -ErrorAction SilentlyContinue) -and -not $Force) {
    throw "Task already exists: $TaskName (use -Force to overwrite)"
}

if ($Force) {
    Unregister-ScheduledTask -TaskName $shortName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
}

Register-ScheduledTask `
    -TaskName $shortName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Saving the News NEWS-HP-RT weekly re-bench after calendar gate (research_only shadow)."

Write-Host "Registered scheduled task: $TaskName on $DayOfWeek at $RunAt (not_before=$NotBefore)" -ForegroundColor Green
