# Register daily Logos Studio B2B smoke (deploy verify + lemma live + demo preset batch).
param(
    [string]$DailyAt = "07:00",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$taskName = "MKM_LogosStudioB2bDailySmoke_v1"
$script = Join-Path $root "scripts\Invoke-LogosStudioB2bDailySmoke_v1.ps1"
$args = "-NoProfile -ExecutionPolicy Bypass -File `"$script`""

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
Register-ScheduledTask -TaskName $taskName -Action (New-ScheduledTaskAction -Execute "powershell.exe" -Argument $args) -Trigger $trigger -Settings $settings -Description "Logos B2B daily smoke: deploy verify + lemma live + demo preset batch; NON_GATING"
Write-Host "Registered: $taskName at $DailyAt"
Write-Host "Manual: powershell -File scripts\Invoke-LogosStudioB2bDailySmoke_v1.ps1"
