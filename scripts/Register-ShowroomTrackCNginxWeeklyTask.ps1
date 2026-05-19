# Weekly: push jemaai_showroom_ui.conf nginx snippet + reload (api.jemaai.cloud static mirror).
# Assumes daily Showroom-TrackC-Publish-Daily keeps /var/www/jemaai/ current.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-ShowroomTrackCNginxWeeklyTask.ps1
#   powershell ... -Unregister

param(
    [string]$StartTime = "09:40",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "Showroom-TrackC-Nginx-Weekly",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"

$syncScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\sync_showroom_to_vps.ps1"

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
    "-File", "`"$syncScript`"",
    "-WorkspaceRoot", "`"$WorkspaceRoot`"",
    "-NginxSnippetOnly",
    "-ApplyRecommendedNginx"
)
$tr = "$psExe " + ($argParts -join " ")

schtasks /Create /TN $TaskName /SC WEEKLY /D SUN /ST $StartTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to create task $TaskName" }

Write-Host "Created scheduled task: $TaskName (weekly SUN $StartTime)"
Write-Host "Command: $tr"
Write-Host "Verify: scripts\Verify-ShowroomTrackCNginxWeeklyScheduledTask_v1.ps1"
