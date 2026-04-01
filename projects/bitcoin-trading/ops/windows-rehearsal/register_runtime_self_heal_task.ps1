$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Runtime-Self-Heal"
$startTime = "09:12"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$scriptPath = Join-Path $projectRoot "ops\windows-rehearsal\self_heal_runtime_tasks.ps1"

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Runtime self-heal script not found: $scriptPath"
}

$argParts = @(
    "-NoProfile",
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

schtasks /Create /TN $taskName /SC DAILY /ST $startTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create runtime self-heal task. ExitCode=$LASTEXITCODE"
}

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -ne 0) {
    throw "Task create succeeded but query failed for '$taskName'."
}

Write-Host "Created scheduled runtime self-heal task: $taskName"
Write-Host "Start time: $startTime"
Write-Host "Command: $tr"
