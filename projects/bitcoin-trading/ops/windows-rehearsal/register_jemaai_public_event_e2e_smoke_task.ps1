$ErrorActionPreference = "Stop"

$taskName = "Jemaai-PublicEvent-E2E-Smoke"
$startTime = "09:35"
$opsRoot = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"
$smokeScript = Join-Path $opsRoot "run_jemaai_public_event_e2e_smoke.ps1"
$assertScript = Join-Path $opsRoot "assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $smokeScript -Label "jemaai public-event e2e smoke script"

$argParts = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$smokeScript`"",
    "-ApiBaseUrl", "`"https://api.jemaai.cloud`""
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
    throw "Failed to create jemaai e2e smoke task. ExitCode=$LASTEXITCODE"
}

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -ne 0) {
    throw "Task create succeeded but query failed for '$taskName'."
}

Write-Host "Created scheduled jemaai e2e smoke task: $taskName"
Write-Host "Start time: $startTime"
Write-Host "Command: $tr"
