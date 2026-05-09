[CmdletBinding()]
param(
    [string]$TaskName = "MKM-ThreeLens-FeatureGateV2-Daily",
    [string]$DailyAt = "07:25",
    [switch]$Unregister,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Plan {
    param([string]$Message)
    Write-Host "[ThreeLensV2-Task] $Message"
}

if ($Unregister) {
    Write-Plan "Unregister mode for task: $TaskName"
    if ($DryRun) {
        Write-Plan "DryRun: would unregister scheduled task."
        exit 0
    }
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Plan "Task removed: $TaskName"
    } catch {
        Write-Plan "Task not found or remove failed: $TaskName"
    }
    exit 0
}

$parts = $DailyAt.Split(":")
if ($parts.Count -ne 2) {
    throw "DailyAt must be HH:mm format. Received: $DailyAt"
}
[int]$hour = $parts[0]
[int]$minute = $parts[1]
if ($hour -lt 0 -or $hour -gt 23 -or $minute -lt 0 -or $minute -gt 59) {
    throw "DailyAt out of range: $DailyAt"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repoRoot "scripts\Run-ThreeLensFeatureGateV2.ps1"
if (-not (Test-Path $runner)) {
    throw "Runner script missing: $runner"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`""
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($hour).AddMinutes($minute))
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Write-Plan "TaskName=$TaskName"
Write-Plan "DailyAt=$DailyAt"
Write-Plan "Runner=$runner"

if ($DryRun) {
    Write-Plan "DryRun: would register/update scheduled task."
    exit 0
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Run MKM three-lens feature gate v2 daily" `
    -Force | Out-Null

Write-Plan "Task registered: $TaskName"
