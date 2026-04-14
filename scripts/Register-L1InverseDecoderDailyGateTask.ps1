<#
.SYNOPSIS
  Register (or remove) a daily Scheduled Task for L1 inverse decoder daily gate.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_L1InverseDecoder_DailyGate).

.PARAMETER DailyAt
  Local time HH:mm (default: 06:30).

.PARAMETER Mode
  Gate mode passed to runner (warning|block).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_L1InverseDecoder_DailyGate",
    [string]$DailyAt = "06:30",
    [ValidateSet("warning", "block")]
    [string]$Mode = "warning"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_l1_inverse_decoder_daily_gate_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 06:30), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"Set-Location '$workspaceRoot'; py '$runner' --mode $Mode`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily: L1 inverse decoder mixed/swap_typo commercialization gate check and log append."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily $DailyAt local, user=$env:USERNAME, mode=$Mode)"
Write-Host "Runner: $runner"
