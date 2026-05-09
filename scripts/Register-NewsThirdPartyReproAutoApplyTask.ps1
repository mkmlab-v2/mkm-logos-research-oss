<#
.SYNOPSIS
  Register/remove auto-apply task for news third-party reproducibility evidence.

.DESCRIPTION
  Polls dropzone every N minutes and runs Apply-NewsThirdPartyReproFromDropzone.ps1.
  Non-ready state (missing files) exits 2 and is treated as expected standby.
#>
[CmdletBinding()]
param(
    [switch] $Remove,
    [switch] $DryRun,
    [string] $TaskName = "MKM_News_ThirdParty_Repro_AutoApply",
    [int] $IntervalMinutes = 15,
    [string] $RunnerId = "external-runner-auto",
    [string] $Signer = "external-signer-auto"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Apply-NewsThirdPartyReproFromDropzone.ps1"

if ($Remove) {
    if ($DryRun) {
        Write-Host "[DryRun] Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task (if existed): $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if ($IntervalMinutes -lt 5) {
    throw "IntervalMinutes must be >= 5"
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -RunnerId `"$RunnerId`" -Signer `"$Signer`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ($DryRun) {
    Write-Host "[DryRun] TaskName: $TaskName"
    Write-Host "[DryRun] Repeat interval: ${IntervalMinutes}m"
    Write-Host "[DryRun] Command: powershell.exe $argLine"
    exit 0
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Auto-apply news third-party repro evidence from dropzone." -Force | Out-Null
Write-Host "Registered: $TaskName (every $IntervalMinutes minutes)"
Write-Host "Runner: $runner"
exit 0

