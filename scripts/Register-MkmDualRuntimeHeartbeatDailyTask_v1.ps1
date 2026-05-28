<#
.SYNOPSIS
  Register daily Scheduled Task for mkmlife dual-runtime heartbeat (CF + VPS + LoRA pointer).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_DualRuntime_Heartbeat_Daily",
    [string]$DailyAt = "08:15"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    "C:\workspace"
}
$runner = Join-Path $workspaceRoot "scripts\Invoke-MkmDualRuntimeHeartbeat_v1.ps1"

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

$runnerArgs = @(
    "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`""
)
$arg = ($runnerArgs -join " ")

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Daily mkmlife CF smoke + VPS git probe + LoRA pointer (B-track, research_only)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName daily at $DailyAt"
Write-Host "Runner: $runner"
