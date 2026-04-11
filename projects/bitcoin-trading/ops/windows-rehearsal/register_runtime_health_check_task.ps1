$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Runtime-Health-Check"
$startTime = "09:20"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$healthScript = Join-Path $projectRoot "ops\windows-rehearsal\verify_fused_quant_pixel_runtime_health.ps1"
$assertScript = Join-Path $projectRoot "ops\windows-rehearsal\assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $healthScript -Label "Runtime health check script"

$argParts = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$healthScript`""
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
    throw "Failed to create runtime health check task. ExitCode=$LASTEXITCODE"
}

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -ne 0) {
    throw "Task create succeeded but query failed for '$taskName'."
}

Write-Host "Created scheduled runtime health task: $taskName"
Write-Host "Start time: $startTime"
Write-Host "Command: $tr"
