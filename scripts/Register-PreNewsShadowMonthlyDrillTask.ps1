param(
    [switch]$Remove,
    [switch]$DryRun,
    [string]$TaskName = "MKM_PreNewsShadow_Monthly_Drill",
    [int]$DayOfMonth = 1,
    [string]$AtTime = "07:20",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\run_pre_news_shadow_alert_drill_v1.py"

if ($Remove) {
    if ($DryRun) {
        Write-Host "[DryRun] Would remove scheduled task: $TaskName"
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $AtTime -split ':'
if ($parts.Count -lt 2) {
    throw "AtTime must be HH:mm, got: $AtTime"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$startTime = "{0:D2}:{1:D2}" -f $hour, $minute

$cmd = "py -3 `"$runner`""

if ($DryRun) {
    Write-Host "[DryRun] TaskName: $TaskName"
    Write-Host "[DryRun] Trigger : Monthly day=$DayOfMonth at $AtTime"
    Write-Host "[DryRun] Runner  : $runner"
    Write-Host "[DryRun] Command : $cmd"
    exit 0
}

$createArgs = @(
    "/Create",
    "/F",
    "/TN", $TaskName,
    "/SC", "MONTHLY",
    "/D", "$DayOfMonth",
    "/ST", $startTime,
    "/TR", "`"$cmd`"",
    "/RL", "LIMITED",
    "/RU", $env:USERNAME
)
$cp = Start-Process -FilePath "schtasks.exe" -ArgumentList $createArgs -NoNewWindow -Wait -PassThru
if ($cp.ExitCode -ne 0) {
    throw "Failed to register scheduled task via schtasks.exe (exit=$($cp.ExitCode))"
}

Write-Host "Registered scheduled task: $TaskName (monthly day=$DayOfMonth at $AtTime)"
Write-Host "Runner: $runner"

