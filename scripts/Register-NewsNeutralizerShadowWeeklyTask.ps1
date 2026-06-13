param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_NewsNeutralizer_Shadow_Weekly",
    [string]$RunAt = "09:05",
    [ValidateSet("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")]
    [string]$DayOfWeek = "Sunday",
    [int]$MaxCards = 5,
    [int]$MaxClusters = 1,
    [int]$AzureInterCallSleep = 20,
    [switch]$IncludeLive,
    [ValidateSet("auto", "azure", "developer", "vertex")]
    [string]$Billing = "azure",
    [string]$AzureDeployment = "",
    [switch]$UseFixture,
    [switch]$Force,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$shortName = $TaskName.TrimStart("\")

if ($Remove) {
    Unregister-ScheduledTask -TaskName $shortName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "Removed scheduled task: $shortName" -ForegroundColor Yellow
    exit 0
}

$scriptPath = Join-Path $WorkspaceRoot "scripts\Run-NewsNeutralizerShadowChain_v1.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$chainArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"{0}"' -f $scriptPath),
    "-MaxCards", $MaxCards,
    "-MaxClusters", $MaxClusters
)
if ($IncludeLive) {
    $chainArgs += "-Live"
    $chainArgs += "-Billing"
    $chainArgs += $Billing
    if ($AzureInterCallSleep -ge 0) {
        $chainArgs += "-AzureInterCallSleep"
        $chainArgs += $AzureInterCallSleep
    }
    if ($AzureDeployment) {
        $chainArgs += "-AzureDeployment"
        $chainArgs += $AzureDeployment
    }
}
if ($UseFixture) {
    $chainArgs += "-Fixture"
}

$argLine = $chainArgs -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $RunAt
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ((Get-ScheduledTask -TaskName $shortName -ErrorAction SilentlyContinue) -and -not $Force) {
    throw "Task already exists: $shortName (use -Force to overwrite)"
}

if ($Force) {
    Unregister-ScheduledTask -TaskName $shortName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
}

$modeNote = if ($IncludeLive) { "RSS+LLM live (billing=$Billing)" } elseif ($UseFixture) { "fixture dry-run" } else { "RSS dry-run stub (default tier_0)" }
$description = "B-track news neutralizer shadow + deck candidates (research_only; no public deck). Mode: $modeNote."

Register-ScheduledTask `
    -TaskName $shortName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description $description `
    -Force | Out-Null

Write-Host "Registered scheduled task: $shortName on $DayOfWeek at $RunAt (MaxCards=$MaxCards; $modeNote)" -ForegroundColor Green
Write-Host "Verify: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-NewsNeutralizerShadowWeeklyTaskReadiness_v1.ps1"
