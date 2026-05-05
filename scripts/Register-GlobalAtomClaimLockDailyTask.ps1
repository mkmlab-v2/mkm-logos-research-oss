# Register daily task for Global Atom claim lock checks.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Register-GlobalAtomClaimLockDailyTask.ps1
#   powershell ... -StartTime 05:20
#   powershell ... -RunNow
#   powershell ... -Unregister

param(
    [string]$StartTime = "05:20",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "GlobalAtom-ClaimLock-Daily",
    [switch]$RunNow,
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"

$claimCheck = Join-Path $WorkspaceRoot "scripts\check_global_atom_claim_lock_v1.py"
$atomCheck = Join-Path $WorkspaceRoot "scripts\check_global_atom_edge_claim_atom_set_v1.py"
$runScript = Join-Path $WorkspaceRoot "scripts\run_global_atom_claim_lock_daily.ps1"
$assertScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\assert_task_target_exists.ps1"

if (-not $Unregister) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $assertScript -TargetPath $claimCheck -Label "global atom claim lock check script"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $assertScript -TargetPath $atomCheck -Label "global atom atom-set check script"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $assertScript -TargetPath $runScript -Label "global atom claim lock daily runner script"
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
$tr = "$psExe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$runScript"" -WorkspaceRoot ""$WorkspaceRoot"""

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
