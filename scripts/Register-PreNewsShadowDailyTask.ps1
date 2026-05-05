param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "\MKM-PreNews-Shadow-Daily",
    [string]$RunAt = "06:30",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts\run_daily_prophecy_then_pre_news_v1.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$argLine = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"{0}"' -f $scriptPath),
    "-EnablePreNewsShadow",
    "-EnablePreNewsShadowWeeklyReport"
) -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 4) -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ((Get-ScheduledTask -TaskName ($TaskName.TrimStart("\")) -ErrorAction SilentlyContinue) -and -not $Force) {
    throw "Task already exists: $TaskName (use -Force to overwrite)"
}

if ($Force) {
    Unregister-ScheduledTask -TaskName ($TaskName.TrimStart("\")) -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
}

Register-ScheduledTask `
    -TaskName ($TaskName.TrimStart("\")) `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Runs daily prophecy wrapper with pre-news shadow projection and weekly summary."

Write-Host "Registered scheduled task: $TaskName at $RunAt" -ForegroundColor Green

