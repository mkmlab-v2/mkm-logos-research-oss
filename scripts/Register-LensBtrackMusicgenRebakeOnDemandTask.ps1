# Register on-demand Windows task for lens MusicGen rebake (detached worker, no daily schedule).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-LensBtrackMusicgenRebakeOnDemandTask.ps1
#   schtasks /Run /TN "MKM_Lens_Musicgen_Rebake_OnDemand"
#   powershell ... -Unregister

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_Lens_Musicgen_Rebake_OnDemand",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$worker = Join-Path $WorkspaceRoot "scripts\Invoke-LensBtrackMusicgenRebakeWorker_v1.ps1"

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $TaskName > $null 2>&1
$exists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $oldEap

if ($Unregister) {
    if (-not $exists) {
        Write-Host "Unregister: task '$TaskName' not found."
        exit 0
    }
    schtasks /Delete /TN $TaskName /F | Out-Null
    Write-Host "Removed: $TaskName"
    exit 0
}

if ($exists) { schtasks /Delete /TN $TaskName /F | Out-Null }

$psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell.exe" }
$tr = "$psExe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$worker`" -WorkspaceRoot `"$WorkspaceRoot`" -ForceRegen"

schtasks /Create /TN $TaskName /SC ONCE /ST 00:00 /SD 2099/01/01 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to create task $TaskName" }

Write-Host "Created on-demand task: $TaskName"
Write-Host "Run: schtasks /Run /TN `"$TaskName`""
Write-Host "Status: scripts\Run-LensBtrackMusicgenRebakeResume_v1.ps1 -Status"
