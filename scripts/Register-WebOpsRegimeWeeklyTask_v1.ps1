#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly web_ops_regime gate check (drift/dual-alignment; no baseline reseed).

.EXAMPLE
  pwsh -File scripts/Register-WebOpsRegimeWeeklyTask_v1.ps1
  pwsh -File scripts/Register-WebOpsRegimeWeeklyTask_v1.ps1 -Unregister
#>
param(
    [string]$StartTime = "09:18",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_WebOps_Regime_Weekly",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$routine = Join-Path $WorkspaceRoot "scripts\Invoke-WebOpsRegimeWeeklyRoutine_v1.ps1"

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $TaskName > $null 2>&1
$exists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $oldEap

if ($Unregister) {
    if (-not $exists) {
        Write-Host "Unregister: task '$TaskName' not found." -ForegroundColor Yellow
        exit 0
    }
    schtasks /Delete /TN $TaskName /F | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if ($exists) { schtasks /Delete /TN $TaskName /F | Out-Null }

$psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell.exe" }
$argParts = @(
    "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
    "-File", "`"$routine`"",
    "-NoSeedBaselines",
    "-RequireDualAlignment",
    "-FailOnPointerDrift",
    "-SkipLiveCdp"
)
$tr = "$psExe " + ($argParts -join " ")

schtasks /Create /TN $TaskName /SC WEEKLY /D SUN /ST $StartTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to create task $TaskName" }

Write-Host "Created scheduled task: $TaskName (weekly SUN $StartTime)"
Write-Host "Command: $tr"
Write-Host "Verify: scripts\Verify-WebOpsRegimeWeeklyTaskReadiness_v1.ps1"
