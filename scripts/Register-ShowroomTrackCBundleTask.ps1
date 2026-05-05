# Register Windows Task Scheduler job: daily Track C showroom bundle chain (freshness + build + validate).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Register-ShowroomTrackCBundleTask.ps1
#   powershell ... -StartTime 09:28
#   powershell ... -Unregister  # remove task only

param(
    [string]$StartTime = "09:28",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "Showroom-TrackC-Bundle-Daily",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"

$chainScript = Join-Path $WorkspaceRoot "scripts\build_showroom_track_c_bundle_chain_v1.ps1"
$assertScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\assert_task_target_exists.ps1"

if (-not $Unregister) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $assertScript -TargetPath $chainScript -Label "Track C showroom bundle chain"
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
    "-File", "`"$chainScript`"",
    "-WorkspaceRoot", "`"$WorkspaceRoot`""
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
