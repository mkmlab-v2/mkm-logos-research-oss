param(
    [string]$StartTime = "09:00"
)

$ErrorActionPreference = "Stop"

$taskName = "Compression-Stub-Ensure-Daily"
$opsRoot = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"
$ensureScript = Join-Path $opsRoot "ensure_compression_stub.ps1"
$assertScript = Join-Path $opsRoot "assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $ensureScript -Label "compression stub ensure script"

$argParts = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$ensureScript`""
)
$tr = "powershell " + ($argParts -join " ")

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $taskName /F | Out-Null
}

schtasks /Create /TN $taskName /SC DAILY /ST $StartTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create compression stub ensure task. ExitCode=$LASTEXITCODE"
}

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -ne 0) {
    throw "Task create succeeded but query failed for '$taskName'."
}

Write-Host "Created scheduled compression stub task: $taskName"
Write-Host "Start time: $StartTime"
Write-Host "Command: $tr"
