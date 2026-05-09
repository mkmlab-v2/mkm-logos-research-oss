# Register Windows Task Scheduler job for guarded showroom VPS deploy.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Register-ShowroomGuardedDeployTask.ps1
#   powershell ... -StartTime 09:40
#   powershell ... -SshIdentityFile "C:\Users\PRO\.ssh\hostinger_mkmlife"
#   powershell ... -RunNow
#   powershell ... -Unregister

param(
    [string]$StartTime = "09:40",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "Showroom-Guarded-VPS-Deploy-Daily",
    [string]$SshIdentityFile = "C:\Users\PRO\.ssh\hostinger_mkmlife",
    [switch]$RunNow,
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"

$deployScript = Join-Path $WorkspaceRoot "scripts\run_showroom_vps_guarded_deploy.ps1"
$assertScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\assert_task_target_exists.ps1"

if (-not $Unregister) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $assertScript -TargetPath $deployScript -Label "showroom guarded VPS deploy script"
}

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $TaskName > $null 2>&1
$exists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $oldEap

if ($Unregister) {
    if (-not $exists) {
        Write-Host "Unregister: task '$TaskName' not found (nothing to do)." -ForegroundColor Yellow
        exit 0
    }
    schtasks /Delete /TN $TaskName /F | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to delete task $TaskName"
    }
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if ($exists) {
    schtasks /Delete /TN $TaskName /F | Out-Null
}

$psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell.exe" }
$argParts = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$deployScript`"",
    "-SshIdentityFile", "`"$SshIdentityFile`""
)
$tr = "$psExe " + ($argParts -join " ")

schtasks /Create /TN $TaskName /SC DAILY /ST $StartTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task. ExitCode=$LASTEXITCODE Task=$TaskName"
}

$ErrorActionPreference = "Continue"
schtasks /Query /TN $TaskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -ne 0) {
    throw "Task create succeeded but query failed for '$TaskName'."
}

Write-Host "Created scheduled task: $TaskName"
Write-Host "Start time (daily): $StartTime"
Write-Host "Command: $tr"

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to run task immediately: $TaskName"
    }
    Write-Host "Triggered task now: $TaskName"
}
