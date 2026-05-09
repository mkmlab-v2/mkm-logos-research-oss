param(
  [string]$TaskName = "Darkflow-BTrack-Chain-Daily",
  [string]$At = "09:20",
  [ValidateSet("dotenv", "user", "process")]
  [string]$EnvSourceMode = "process",
  [switch]$EnableAutoProfileSwitch = $true,
  [switch]$Force
)

$ErrorActionPreference = "Stop"

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $workspaceRoot "scripts\run_darkflow_btrack_chain_v1.ps1"

if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner not found: $runner"
}

$argParts = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", "`"$runner`"",
  "-EnvSourceMode", $EnvSourceMode
)
if ($EnableAutoProfileSwitch) {
  $argParts += "-EnableAutoProfileSwitch"
}
$argLine = ($argParts -join " ")

$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument $argLine `
  -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew

if ($Force -and (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Dark Flow B-track chain (override + gates + trend + weekly governance + autoswitch)"

Write-Host "Registered task: $TaskName @ $At"
Write-Host "Task arguments: $argLine"
