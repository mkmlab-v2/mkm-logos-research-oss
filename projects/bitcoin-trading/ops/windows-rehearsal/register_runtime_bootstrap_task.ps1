$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Runtime-Bootstrap-Automation"
$startTime = "09:10"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$bootstrapScript = Join-Path $projectRoot "ops\windows-rehearsal\bootstrap_runtime_automation.ps1"
$assertScript = Join-Path $projectRoot "ops\windows-rehearsal\assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $bootstrapScript -Label "Runtime bootstrap script"

$argParts = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$bootstrapScript`""
)
$tr = "powershell " + ($argParts -join " ")

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $taskName /F | Out-Null
}

schtasks /Create /TN $taskName /SC DAILY /ST $startTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create runtime bootstrap task. ExitCode=$LASTEXITCODE"
}

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -ne 0) {
    throw "Task create succeeded but query failed for '$taskName'."
}

Write-Host "Created scheduled runtime bootstrap task: $taskName"
Write-Host "Start time: $startTime"
Write-Host "Command: $tr"
