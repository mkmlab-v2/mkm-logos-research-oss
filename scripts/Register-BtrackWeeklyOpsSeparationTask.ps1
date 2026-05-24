#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly task: B-track VPS/prophecy separation observability (Sunday default 10:15).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-BTrack-WeeklyOpsSeparation",
    [string]$SundayAt = "10:15",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Invoke-BtrackWeeklyOpsSeparation_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "Missing: $runner" }

if ($Remove) {
    schtasks.exe /Delete /TN $TaskName /F 2>$null
    Write-Host "[DONE] Removed: $TaskName" -ForegroundColor Yellow
    exit 0
}

$tr = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""
schtasks.exe /Create /TN $TaskName /SC WEEKLY /D SUN /ST $SundayAt /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) { throw "schtasks exit $LASTEXITCODE" }
Write-Host "[OK] Registered $TaskName Sunday $SundayAt" -ForegroundColor Green
