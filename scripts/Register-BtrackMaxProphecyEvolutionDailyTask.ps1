#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily MKM B-track max prophecy evolution chain (tier3; Disabled by default).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-BtrackMaxProphecyEvolutionDailyTask.ps1 -At "07:30"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-BtrackMaxProphecyEvolutionDailyTask.ps1 -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_BtrackMaxProphecyEvolution_Daily",
    [string]$At = "07:30",
    [ValidateSet("research", "ops")]
    [string]$HoldoutGateProfile = "research",
    [switch]$EnableOnRegister,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Run-BtrackMaxProphecyEvolutionDailyChain_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "Missing runner: $runner" }

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -HoldoutGateProfile $HoldoutGateProfile"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$desc = "B-track max prophecy evolution daily chain; research_only; send_gate HOLD; reports/btrack_max_prophecy_evolution_daily_chain_v1_latest.json"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

if (-not $EnableOnRegister) {
    Disable-ScheduledTask -TaskName $TaskName | Out-Null
    Write-Host "[OK] Registered DISABLED: $TaskName at $At (Enable-ScheduledTask to activate)" -ForegroundColor Green
} else {
    Write-Host "[OK] Registered ENABLED: $TaskName at $At" -ForegroundColor Green
}
