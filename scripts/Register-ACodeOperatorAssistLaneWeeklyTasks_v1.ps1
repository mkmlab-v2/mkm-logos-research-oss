#Requires -Version 5.1
<#
.SYNOPSIS
  Register both A-code operator-assist weekly tasks: full + light profiles.

.DESCRIPTION
  - MKM-ACode-OperatorAssistLane-Weekly — Sunday 09:05 full (multiday)
  - MKM-ACode-OperatorAssistLane-Weekly-Light — Sunday 09:18 light (-SkipGovernorBundle)

.EXAMPLE
  pwsh -File scripts/Register-ACodeOperatorAssistLaneWeeklyTasks_v1.ps1 -DryRun
  pwsh -File scripts/Register-ACodeOperatorAssistLaneWeeklyTasks_v1.ps1 -Remove
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Strict,
    [switch]$DryRun,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$register = Join-Path $WorkspaceRoot "scripts\Register-ACodeOperatorAssistLaneWeeklyTask_v1.ps1"
if (-not (Test-Path -LiteralPath $register)) {
    throw "Missing: $register"
}

$profiles = @(
    @{
        TaskName = "MKM-ACode-OperatorAssistLane-Weekly"
        RunAt = "09:05"
        SkipGovernorBundle = $false
    },
    @{
        TaskName = "MKM-ACode-OperatorAssistLane-Weekly-Light"
        RunAt = "09:18"
        SkipGovernorBundle = $true
    }
)

if ($Remove) {
    foreach ($p in $profiles) {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File $register `
            -WorkspaceRoot $WorkspaceRoot -TaskName $p.TaskName -Remove
    }
    Write-Host "[REMOVED] both operator-assist weekly tasks" -ForegroundColor Yellow
    exit 0
}

foreach ($p in $profiles) {
    $args = @(
        "-WorkspaceRoot", $WorkspaceRoot,
        "-TaskName", $p.TaskName,
        "-RunAt", $p.RunAt
    )
    if ($p.SkipGovernorBundle) { $args += "-SkipGovernorBundle" }
    if ($Strict) { $args += "-Strict" }
    if ($DryRun) { $args += "-DryRun" }
    & pwsh -NoProfile -ExecutionPolicy Bypass -File $register @args
    if ($LASTEXITCODE -ne 0) { throw "register failed for $($p.TaskName)" }
}

$meta = [ordered]@{
    schema = "a_code_operator_assist_lane_weekly_tasks_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    profiles = $profiles
    verify_command = "pwsh -File scripts/Verify-ACodeOperatorAssistLaneReadiness_v1.ps1 -RequireBothWeeklyTasks"
}
$out = Join-Path $WorkspaceRoot "reports\a_code_operator_assist_lane_weekly_tasks_latest.json"
$meta | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $out -Encoding utf8
Write-Host "Wrote $out" -ForegroundColor DarkGray
exit 0
