param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "GeneralProphecyHoldoutEvolutionWeeklyV1",
    [ValidateSet("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")]
    [string]$Day = "SUN",
    [string]$At = "09:00",
    [ValidateSet("research", "ops")]
    [string]$HoldoutGateProfile = "ops",
    [ValidateSet("true", "false")]
    [string]$IncludeLogosV2 = "true",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$refresh = Join-Path $WorkspaceRoot "scripts\run_general_prophecy_daily_queue_refresh_v1.ps1"
if (-not (Test-Path -LiteralPath $refresh)) {
    throw "Missing script: $refresh"
}

$taskRun = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$refresh`" -HoldoutGateProfile $HoldoutGateProfile -IncludeLogosV2 $IncludeLogosV2"

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
    throw "Failed to register weekly evolution task via schtasks.exe (exit=$LASTEXITCODE)"
}

$query = schtasks /Query /TN "\$TaskName" /V /FO LIST | Out-String
Write-Host $query
