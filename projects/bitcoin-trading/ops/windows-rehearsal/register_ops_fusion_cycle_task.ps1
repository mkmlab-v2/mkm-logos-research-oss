param(
    [string]$StartTime = "00:05",
    [ValidateRange(5, 1440)]
    [int]$RepeatMinutes = 60,
    [string]$Phase1Mode = "weekly_lite"
)

$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Ops-Fusion-Cycle-Auto"
$opsRoot = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"
$scriptPath = Join-Path $opsRoot "run_ops_fusion_cycle.ps1"
$assertScript = Join-Path $opsRoot "assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $scriptPath -Label "ops fusion cycle script"

$argParts = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$scriptPath`"",
    "-Phase1Mode", $Phase1Mode
)
$tr = "powershell " + ($argParts -join " ")

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $taskName /F | Out-Null
}

schtasks /Create /TN $taskName /SC MINUTE /MO $RepeatMinutes /ST $StartTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create ops fusion cycle task. ExitCode=$LASTEXITCODE"
}

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $taskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -ne 0) {
    throw "Task create succeeded but query failed for '$taskName'."
}

Write-Host "Created scheduled ops fusion cycle task: $taskName"
Write-Host "Start time: $StartTime"
Write-Host "Repeat interval (minutes): $RepeatMinutes"
Write-Host "Phase1Mode: $Phase1Mode"
Write-Host "Command: $tr"
