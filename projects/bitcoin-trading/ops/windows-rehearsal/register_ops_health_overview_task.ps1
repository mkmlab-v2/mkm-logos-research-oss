param(
    [string]$StartTime = "10:10"
)

$ErrorActionPreference = "Stop"

$taskName = "Ops-Health-Overview-Daily"
$opsRoot = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"
$scriptPath = Join-Path $opsRoot "run_ops_health_overview_and_append.ps1"
$assertScript = Join-Path $opsRoot "assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $scriptPath -Label "ops health overview build script"

$argParts = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$scriptPath`""
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
    throw "Failed to create ops health overview task. ExitCode=$LASTEXITCODE"
}

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -ne 0) {
    throw "Task create succeeded but query failed for '$taskName'."
}

Write-Host "Created scheduled ops health overview task: $taskName"
Write-Host "Start time: $StartTime"
Write-Host "Command: $tr"
