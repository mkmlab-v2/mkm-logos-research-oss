<#
.SYNOPSIS
  Register (or remove) a daily Variant-B homepage smoke task.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_VariantB_Smoke_Daily",
    [string]$DailyAt = "09:10"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_variant_b_smoke_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ":"
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 09:10), got: $DailyAt"
}
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $at
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily smoke check for mkmlab Variant-B links and smartfarm parameter handoff."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (Daily $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"

$webhook = $env:VARIANT_B_SMOKE_WEBHOOK_URL
if ([string]::IsNullOrWhiteSpace($webhook)) {
    $webhook = $env:OPS_ALARM_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($webhook)) {
    Write-Warning "No webhook configured. Set VARIANT_B_SMOKE_WEBHOOK_URL (or OPS_ALARM_WEBHOOK_URL) for failure alerts."
}
else {
    Write-Host "Webhook configured for failure alerts." -ForegroundColor Green
}
