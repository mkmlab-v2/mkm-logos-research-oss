<#
.SYNOPSIS
  Register daily MKM Morning Beans build + mkmlife export (B-track, research_only).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_MorningBeans_Daily",
    [string]$DailyAt = "07:05",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Run-MkmMorningBeansDailyChain_v1.ps1"

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
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`"" `
    -WorkingDirectory $WorkspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "MKM Morning Beans: build feed + mkmlife card export. [HYPO] B-track; no live trading."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName daily at $DailyAt ($runner)"
Write-Host "Verify: powershell -File scripts\Verify-MkmMorningBeansDailyScheduledTask_v1.ps1"
Write-Host "Remove: powershell -File scripts\Register-MkmMorningBeansDailyTask.ps1 -Remove"
