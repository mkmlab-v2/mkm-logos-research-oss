param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "GeneralProphecyDailyQueueV1",
    [string]$DailyAt = "09:00",
    [ValidateSet("research", "ops")]
    [string]$HoldoutGateProfile = "ops",
    [ValidateSet("true", "false")]
    [string]$IncludeLogosV2 = "true",
    [ValidateSet("true", "false")]
    [string]$EnableLogosResponseV1Retry = "false",
    [ValidateSet("true", "false")]
    [string]$EnableLogosResponseQualityScore = "true",
    [ValidateSet("true", "false")]
    [string]$EnableLogosResponseQualityAlert = "true",
    [double]$LogosResponseQualityMinOverall = 8.0,
    [string]$LogosResponseV1PrimaryInput = "docs/final/artifacts/logos_response_v1_llm_raw_latest.txt",
    [string]$LogosResponseV1RetryInput = "docs/final/artifacts/logos_response_v1_llm_retry_latest.txt",
    [int]$LogosResponseV1MaxAttempts = 2,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts\run_general_prophecy_daily_queue_refresh_v1.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$taskRunParts = @("powershell -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"")
if ($HoldoutGateProfile -ne "research") {
    $taskRunParts += "-HoldoutGateProfile $HoldoutGateProfile"
}
# Always emit explicit token so check_general_prophecy_task_profile_guard_v1.py can verify scheduled intent.
$taskRunParts += "-IncludeLogosV2 $IncludeLogosV2"
if ($EnableLogosResponseV1Retry -ne "false") {
    $taskRunParts += "-EnableLogosResponseV1Retry $EnableLogosResponseV1Retry"
}
if ($EnableLogosResponseQualityScore -ne "true") {
    $taskRunParts += "-EnableLogosResponseQualityScore $EnableLogosResponseQualityScore"
}
if ($EnableLogosResponseQualityAlert -ne "true") {
    $taskRunParts += "-EnableLogosResponseQualityAlert $EnableLogosResponseQualityAlert"
}
if ($LogosResponseQualityMinOverall -ne 8.0) {
    $taskRunParts += "-LogosResponseQualityMinOverall $LogosResponseQualityMinOverall"
}
if ($LogosResponseV1PrimaryInput -ne "docs/final/artifacts/logos_response_v1_llm_raw_latest.txt") {
    $taskRunParts += "-LogosResponseV1PrimaryInput `"$LogosResponseV1PrimaryInput`""
}
if ($LogosResponseV1RetryInput -ne "docs/final/artifacts/logos_response_v1_llm_retry_latest.txt") {
    $taskRunParts += "-LogosResponseV1RetryInput `"$LogosResponseV1RetryInput`""
}
if ($LogosResponseV1MaxAttempts -ne 2) {
    $taskRunParts += "-LogosResponseV1MaxAttempts $LogosResponseV1MaxAttempts"
}
$taskRun = $taskRunParts -join " "
$createArgs = @(
    "/Create",
    "/TN", $TaskName,
    "/SC", "DAILY",
    "/ST", $DailyAt,
    "/TR", $taskRun,
    "/F"
)

if ($WhatIf) {
    Write-Host "[WhatIf] schtasks.exe $($createArgs -join ' ')"
    exit 0
}

& schtasks.exe @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register task via schtasks.exe (exit=$LASTEXITCODE)"
}

$query = schtasks /Query /TN "\$TaskName" /V /FO LIST | Out-String
Write-Host $query
