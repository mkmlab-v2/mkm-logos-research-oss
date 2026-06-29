#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly B-track predictability harness (gate + Brier drift log).

.DESCRIPTION
  Default SUN 09:10 KST — after general prophecy holdout evolution (09:00) when both registered.
  research_only · no live orders.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_Btrack_Predictability_Harness_Weekly",
    [ValidateSet("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")]
    [string]$Day = "SUN",
    [string]$At = "09:10",
    [switch]$WhatIf,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$routine = Join-Path $WorkspaceRoot "scripts\Invoke-BtrackPredictabilityHarnessRoutine_v1.ps1"
if (-not (Test-Path -LiteralPath $routine)) {
    throw "Missing script: $routine"
}

if ($Remove) {
    schtasks /Delete /TN "\$TaskName" /F 2>$null
    Write-Host "Removed task (if existed): $TaskName"
    exit 0
}

$taskRun = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$routine`""
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
    throw "Failed to register predictability harness task (exit=$LASTEXITCODE)"
}

schtasks /Query /TN "\$TaskName" /V /FO LIST | Out-String | Write-Host
