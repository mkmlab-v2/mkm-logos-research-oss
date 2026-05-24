#Requires -Version 5.1
<#
.SYNOPSIS
  Daily PersonaDiary guide package refresh (default 07:15) — fortune + public JSON mirror.

.DESCRIPTION
  Runs refresh_personadiary_profile_packages_v1.py (all profiles in registry).
  Pair with MKM-Telegram-Minimal-Daily-Digest (08:28) if both enabled.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$At = "07:15",
    [string]$TaskName = "MKM-Personadiary-Daily-Guide-Refresh",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[REMOVED] $TaskName" -ForegroundColor Yellow
    exit 0
}

$refresh = Join-Path $WorkspaceRoot "scripts\refresh_personadiary_profile_packages_v1.py"
if (-not (Test-Path -LiteralPath $refresh)) {
    throw "Missing: $refresh"
}

$loader = @'
Set-Location -LiteralPath '__WORKSPACE__'
py scripts\refresh_personadiary_profile_packages_v1.py --skip-regenerate --report-json reports\personadiary_profile_refresh_latest.json
exit $LASTEXITCODE
'@
$loader = $loader.Replace('__WORKSPACE__', $WorkspaceRoot.Replace("'", "''"))
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"$loader`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Daily PersonaDiary package refresh (profiles registry -> public/data)." -Force | Out-Null

$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] $TaskName at $At Next=$($i.NextRunTime)" -ForegroundColor Green
