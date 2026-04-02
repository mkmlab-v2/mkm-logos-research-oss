param(
    [string]$StartTime = "10:20",
    [ValidateSet("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")]
    [string]$WeeklyDay = "MON"
)

$ErrorActionPreference = "Stop"

$taskName = "Ops-Weekly-Digest"
$opsRoot = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"
$scriptPath = Join-Path $opsRoot "generate_ops_weekly_digest.ps1"
$assertScript = Join-Path $opsRoot "assert_task_target_exists.ps1"

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Script not found: $scriptPath"
}

if (Test-Path -LiteralPath $assertScript) {
    & $assertScript -TargetPath $scriptPath -Label "$taskName target script" | Out-Null
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $WeeklyDay -At $StartTime
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null

[pscustomobject]@{
    task_name = $taskName
    start_time = $StartTime
    weekly_day = $WeeklyDay
    target_script = $scriptPath
} | ConvertTo-Json -Depth 4
