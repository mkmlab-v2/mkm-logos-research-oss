param(
    [string]$Name = "user",
    [int]$Year = 1973,
    [int]$Month = 12,
    [int]$Day = 10,
    [int]$Hour = 4,
    [int]$Minute = 30,
    [int]$Second = 0,
    [string]$IanaTz = "Asia/Seoul",
    [switch]$IsMale,
    [string]$UserPrompt = "",
    [int]$AnnualStartYear = 2026,
    [int]$AnnualYears = 5,
    [int]$MonthlyMonthsPerYear = 3
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
Set-Location $workspaceRoot

$argsList = @(
    "scripts\run_myeongni_autobot_v1.py",
    "--name", $Name,
    "--local", "$Year", "$Month", "$Day", "$Hour", "$Minute", "$Second",
    "--iana-tz", $IanaTz,
    "--annual-start-year", "$AnnualStartYear",
    "--annual-years", "$AnnualYears",
    "--monthly-months-per-year", "$MonthlyMonthsPerYear",
    "--user-prompt", $UserPrompt
)
if ($IsMale) { $argsList += "--is-male" }

& py @argsList
exit $LASTEXITCODE

