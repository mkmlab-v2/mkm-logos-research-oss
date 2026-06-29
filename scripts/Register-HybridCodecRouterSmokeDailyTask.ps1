#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily Task Scheduler job for WTT hybrid codec router smoke (B-track, no Track A write).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-HybridCodecRouterSmokeDailyTask.ps1 -At "09:20"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-HybridCodecRouterSmokeDailyTask.ps1 -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_HybridCodec_OperationalSoak_Loop",
    [string]$At = "09:20",
    [switch]$RunWhenLoggedOff,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$pyCmd = Get-Command py -ErrorAction SilentlyContinue
$py = if ($pyCmd) { $pyCmd.Source } else { "py" }

$child = "scripts\check_compression_hybrid_codec_router_smoke_v1.py"
$childPath = Join-Path $WorkspaceRoot $child
if (-not (Test-Path -LiteralPath $childPath)) {
    throw "Missing smoke script: $childPath"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$argLine = "$child"
$action = New-ScheduledTaskAction -Execute $py -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ($RunWhenLoggedOff) {
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "[OK] Registered: $TaskName daily at $At" -ForegroundColor Green
Write-Host "  Child: $py $child (WTT hybrid smoke; Track A write forbidden)" -ForegroundColor DarkGray
