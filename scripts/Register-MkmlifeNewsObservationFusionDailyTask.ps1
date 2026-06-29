<#
.SYNOPSIS
  Register (or remove) a daily Scheduled Task for the mkmlife news Observation Deck fusion chain.

.DESCRIPTION
  Runs Run-MkmlifeNewsObservationFusionChain_v1.ps1 (B-track, research_only) to refresh
  docs/final/artifacts/news_observation_v1_latest.jsonl -> deck JSON -> mkmlife public copy.
  Deploy is OFF by default; pass -RegisterWithDeploy to include -DeployMkmlifeAssets in the
  scheduled action (asset-only wrangler deploy; secrets stay in .env, never in the task action).

.NOTES
  Verify after registration: scripts/Verify-MkmlifeNewsObservationFusionScheduledTask_v1.ps1
  No Track A / live trading coupling. [HYPO] lane only.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Mkmlife_NewsObservationFusion_Daily",
    [string]$DailyAt = "07:30",
    [int]$MaxCards = 7,
    [switch]$SkipFetchRss,
    [switch]$SkipBench,
    [switch]$RegisterWithDeploy
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-MkmlifeNewsObservationFusionChain_v1.ps1"

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
    throw "DailyAt must be HH:mm (e.g. 07:30), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$runnerArgs = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`"",
    "-MaxCards", "$MaxCards"
)
if (-not $SkipFetchRss) {
    $runnerArgs += "-FetchRss"
}
if ($SkipBench) {
    $runnerArgs += "-SkipBench"
}
if ($RegisterWithDeploy) {
    $runnerArgs += "-DeployMkmlifeAssets"
}
$argLine = $runnerArgs -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$deployLabel = if ($RegisterWithDeploy) { "deploy=assets" } else { "deploy=off" }
$description = "Daily mkmlife news Observation Deck fusion chain (B-track research_only; $deployLabel). No Track A / live trading coupling."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily at $DailyAt, user=$env:USERNAME, $deployLabel)"
Write-Host "Runner: $runner"
Write-Host "Argument: $argLine"
