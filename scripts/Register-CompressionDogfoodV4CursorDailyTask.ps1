<#
.SYNOPSIS
  Register (or remove) daily Scheduled Task for compression dogfood v4 cursor auto chain.

.DESCRIPTION
  Runs: scripts/Run-CompressionDogfoodV4CursorAutoChain_v1.ps1
  B-track research_only automation (v4 cursor transcript corpus -> intake -> briefing refresh).
  No Track A / live / external SEND coupling.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Compression_Dogfood_V4_Cursor_Daily",
    [string]$DailyAt = "06:55",
    [string]$WorkspaceRoot = "",
    [switch]$RunWhenLoggedOff,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$runner = Join-Path $resolvedRoot "scripts\Run-CompressionDogfoodV4CursorAutoChain_v1.ps1"

if ($Remove) {
    if ($WhatIfOnly) {
        Write-Host "[WhatIf] remove scheduled task: $TaskName" -ForegroundColor DarkGray
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 06:55), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $resolvedRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 90)

$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$description = "Daily compression dogfood v4 cursor auto chain (research_only, send_gate HOLD)."

if ($WhatIfOnly) {
    Write-Host "[WhatIf] register scheduled task: $TaskName (daily $DailyAt, logon=$logonType)" -ForegroundColor DarkGray
    Write-Host "runner: $runner" -ForegroundColor DarkGray
    exit 0
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Registered scheduled task: $TaskName (daily at $DailyAt, user=$env:USERNAME, logon=$logonType)"
Write-Host "  NextRunTime: $($taskInfo.NextRunTime)"
Write-Host "Runner: $runner"

