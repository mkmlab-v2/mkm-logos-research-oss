# Register daily Logos Studio telemetry aggregation (ECS + feedback summaries).
param(
    [string]$DailyAt = "06:30",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$taskName = "MKM_LogosStudioTelemetryDaily_v1"
$script = Join-Path $root "scripts\Invoke-LogosStudioTelemetryRoutine_v1.ps1"
$args = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -IncludeVpsPull"

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($Remove) {
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Removed: $taskName"
    } else {
        Write-Host "Not registered: $taskName"
    }
    exit 0
}

if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$trigger = New-ScheduledTaskTrigger -Daily -At $DailyAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action (New-ScheduledTaskAction -Execute "powershell.exe" -Argument $args) -Trigger $trigger -Settings $settings -Description "Logos Studio ECS+feedback telemetry; B-track NON_GATING; VPS pull optional"
Write-Host "Registered: $taskName at $DailyAt (with -IncludeVpsPull)"
Write-Host "SSOT: add \\MKM_LogosStudioTelemetryDaily_v1 to tier3_optional_active before Ready if EnforceSoloBand applies"
