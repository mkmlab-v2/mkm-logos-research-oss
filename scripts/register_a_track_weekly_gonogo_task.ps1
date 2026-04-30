<# 
.SYNOPSIS
  Register (or remove) Windows Scheduled Task for weekly A-Track Go/No-Go.

.DESCRIPTION
  Creates a weekly task that runs:
    C:\workspace\scripts\run_a_track_weekly_check.ps1 -OnSystemError <no_go|hold_s1>
  (default로 external message claim guard 선검사 포함)

.PARAMETER Remove
  If set, unregister the task.

.PARAMETER TaskName
  Scheduled Task name.

.PARAMETER EnvironmentSuffix
  TaskName 뒤에 붙일 환경 접미사(예: Dev, Prod).

.PARAMETER WeeklyOn
  Day of week.

.PARAMETER At
  Time in HH:mm (24h).

.PARAMETER OnSystemError
  run_a_track_weekly_check.ps1 에 전달할 시스템 에러 정책.

.PARAMETER EnableClaimGuard
  external message claim guard 선검사를 명시적으로 활성화(기본값).

.PARAMETER DisableClaimGuard
  external message claim guard 선검사를 비활성화.

.PARAMETER SkipClaimGuard
  DisableClaimGuard와 동일한 레거시 별칭.

.PARAMETER DryRun
  스케줄러 등록/삭제 없이 계산된 설정만 출력.

.EXAMPLE
  # Dev: hold_s1 + claim guard 비활성 + 월요일 09:35
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register_a_track_weekly_gonogo_task.ps1 `
    -TaskName "A-Track Weekly GoNoGo" -EnvironmentSuffix Dev `
    -WeeklyOn MON -At 09:35 -OnSystemError hold_s1 -DisableClaimGuard

.EXAMPLE
  # Prod: no_go + claim guard 활성 + 월요일 09:30
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register_a_track_weekly_gonogo_task.ps1 `
    -TaskName "A-Track Weekly GoNoGo" -EnvironmentSuffix Prod `
    -WeeklyOn MON -At 09:30 -OnSystemError no_go -EnableClaimGuard

.EXAMPLE
  # 등록 후 수동 트리거 + 상태 확인
  schtasks /Run /TN "A-Track Weekly GoNoGo-Dev"
  schtasks /Run /TN "A-Track Weekly GoNoGo-Prod"
  schtasks /Query /TN "A-Track Weekly GoNoGo-Dev" /V /FO LIST
  schtasks /Query /TN "A-Track Weekly GoNoGo-Prod" /V /FO LIST
#>

param(
  [switch]$Remove,
  [string]$TaskName = "A-Track Weekly GoNoGo",
  [string]$EnvironmentSuffix = "",
  [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
  [string]$WeeklyOn = "MON",
  [string]$At = "09:30",
  [ValidateSet("no_go","hold_s1")]
  [string]$OnSystemError = "no_go",
  [switch]$EnableClaimGuard,
  [switch]$DisableClaimGuard,
  [switch]$SkipClaimGuard,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_a_track_weekly_check.ps1"
$resolvedTaskName = $TaskName
if (-not [string]::IsNullOrWhiteSpace($EnvironmentSuffix)) {
  $normalizedSuffix = $EnvironmentSuffix.Trim()
  if ($normalizedSuffix.StartsWith("-")) {
    $resolvedTaskName = "$TaskName$normalizedSuffix"
  } else {
    $resolvedTaskName = "$TaskName-$normalizedSuffix"
  }
}

if ($Remove) {
  if ($DryRun) {
    Write-Host "[DryRun] Would remove scheduled task: $resolvedTaskName"
    exit 0
  }
  Unregister-ScheduledTask -TaskName $resolvedTaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task: $resolvedTaskName"
  exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner not found: $runner"
}

$parts = $At -split ':'
if ($parts.Count -lt 2) {
  throw "At must be HH:mm, got: $At"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
if ($hour -lt 0 -or $hour -gt 23 -or $minute -lt 0 -or $minute -gt 59) {
  throw "At out of range (HH:mm): $At"
}

$dayMap = @{
  "MON" = "Monday"
  "TUE" = "Tuesday"
  "WED" = "Wednesday"
  "THU" = "Thursday"
  "FRI" = "Friday"
  "SAT" = "Saturday"
  "SUN" = "Sunday"
}
$daysOfWeek = $dayMap[$WeeklyOn]

$effectiveDisableClaimGuard = ($DisableClaimGuard -or $SkipClaimGuard)
if ($EnableClaimGuard -and $effectiveDisableClaimGuard) {
  throw "EnableClaimGuard and DisableClaimGuard(SkipClaimGuard) cannot be used together."
}

$runnerArgs = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -OnSystemError $OnSystemError"
if ($effectiveDisableClaimGuard) {
  $runnerArgs += " -SkipClaimGuard"
}
$claimGuardMode = if ($effectiveDisableClaimGuard) { "disabled" } else { "enabled" }
$envLabel = if ([string]::IsNullOrWhiteSpace($EnvironmentSuffix)) { "default" } else { $EnvironmentSuffix.Trim() }
$taskDescription = "Weekly A-Track Go/No-Go (env=$envLabel, on_error=$OnSystemError, claim_guard=$claimGuardMode)"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument $runnerArgs

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $daysOfWeek -At $At

$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# Interactive login so user context + .env reads behave like local runs.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ($DryRun) {
  Write-Host "[DryRun] TaskName: $resolvedTaskName"
  Write-Host "[DryRun] BaseTaskName: $TaskName"
  Write-Host "[DryRun] EnvironmentSuffix: $EnvironmentSuffix"
  Write-Host "[DryRun] WeeklyOn: $WeeklyOn ($daysOfWeek)"
  Write-Host "[DryRun] At: $At"
  Write-Host "[DryRun] OnSystemError: $OnSystemError"
  Write-Host "[DryRun] Runner: $runner"
  Write-Host "[DryRun] RunnerArgs: $runnerArgs"
  Write-Host "[DryRun] EnableClaimGuard: $([bool](-not $effectiveDisableClaimGuard))"
  Write-Host "[DryRun] DisableClaimGuard: $([bool]$effectiveDisableClaimGuard)"
  exit 0
}

Register-ScheduledTask `
  -TaskName $resolvedTaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal `
  -Description $taskDescription `
  -Force | Out-Null

Write-Host "Registered scheduled task: $resolvedTaskName"
Write-Host "WeeklyOn: $WeeklyOn ($daysOfWeek) At: $At"
Write-Host "Runner: $runner"
Write-Host "RunnerArgs: $runnerArgs"
Write-Host "Description: $taskDescription"

