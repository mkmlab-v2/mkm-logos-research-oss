param(
  [string]$TaskName = "No1kmedi-5Axis-Kpi-Weekly",
  [string]$DayOfWeek = "Sunday",
  [string]$At = "07:10",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runCmd = "cd /d `"$repoRoot`" && npm run build:5axis-kpi-board && npm run check:5axis-kpi-board-schema"
$dayMap = @{
  "Sunday" = "SUN"
  "Monday" = "MON"
  "Tuesday" = "TUE"
  "Wednesday" = "WED"
  "Thursday" = "THU"
  "Friday" = "FRI"
  "Saturday" = "SAT"
}
$taskDay = if ($dayMap.ContainsKey($DayOfWeek)) { $dayMap[$DayOfWeek] } else { $DayOfWeek.ToUpperInvariant() }

if ($DryRun) {
  Write-Host "[DryRun] TaskName: $TaskName"
  Write-Host "[DryRun] Schedule: weekly / $taskDay / $At"
  Write-Host "[DryRun] Command: $runCmd"
  exit 0
}

try {
  schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
} catch {
  # Task may not exist on first registration.
}
schtasks /Create /TN $TaskName /SC WEEKLY /D $taskDay /ST $At /TR "cmd.exe /c $runCmd" /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Failed to create scheduled task: $TaskName"
}

Write-Host "[Register-5AxisKpiWeeklyTask] registered: $TaskName ($taskDay $At)"
