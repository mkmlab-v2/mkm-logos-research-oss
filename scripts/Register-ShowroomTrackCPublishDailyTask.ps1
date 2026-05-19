# Register Windows Task Scheduler: daily Track C showroom publish (bundle + ingest + VPS sync + smoke).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-ShowroomTrackCPublishDailyTask.ps1
#   powershell ... -StartTime 09:32
#   powershell ... -ApplyRecommendedNginx   # weekly nginx snippet refresh on VPS
#   powershell ... -Unregister

param(
    [string]$StartTime = "09:32",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "Showroom-TrackC-Publish-Daily",
    [switch]$ApplyRecommendedNginx,
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"

$routineScript = Join-Path $WorkspaceRoot "scripts\Invoke-ShowroomTrackCPublishRoutine_v1.ps1"
$assertScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\assert_task_target_exists.ps1"

if (-not $Unregister) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $assertScript -TargetPath $routineScript -Label "Showroom Track C publish routine"
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
    "-File", "`"$routineScript`"",
    "-WorkspaceRoot", "`"$WorkspaceRoot`""
)
if ($ApplyRecommendedNginx) {
    $argParts += "-ApplyRecommendedNginx"
}
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
Write-Host "Verify: scripts\Verify-ShowroomTrackCPublishScheduledTask_v1.ps1"
