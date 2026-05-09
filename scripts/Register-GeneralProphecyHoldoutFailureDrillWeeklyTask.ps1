param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "GeneralProphecyHoldoutFailureDrillWeeklyV1",
    [ValidateSet("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")]
    [string]$Day = "SUN",
    [string]$At = "08:30",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts\run_general_prophecy_holdout_failure_drill_v1.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$py = "py"
$taskRun = "$py `"$scriptPath`""

$createArgs = @(
    "/Create",
    "/TN", $TaskName,
    "/SC", "WEEKLY",
    "/D", $Day,
    "/ST", $At,
    "/TR", $taskRun,
    "/F"
)

if ($WhatIf) {
    Write-Host "[WhatIf] schtasks.exe $($createArgs -join ' ')"
    exit 0
}

& schtasks.exe @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register weekly drill task via schtasks.exe (exit=$LASTEXITCODE)"
}

$query = schtasks /Query /TN "\$TaskName" /V /FO LIST | Out-String
Write-Host $query
