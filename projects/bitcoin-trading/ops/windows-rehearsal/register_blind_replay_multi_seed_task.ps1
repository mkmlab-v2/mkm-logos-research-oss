param(
    [string]$StartTime = "10:05"
)

$ErrorActionPreference = "Stop"

$taskName = "BlindReplay-MultiSeed-Daily"
$opsRoot = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"
$scriptPath = Join-Path $opsRoot "run_blind_replay_multi_seed_with_alert.ps1"
$assertScript = Join-Path $opsRoot "assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $scriptPath -Label "blind replay multi seed script"

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
if ($LASTEXITCODE -eq 0) { schtasks /Delete /TN $taskName /F | Out-Null }

schtasks /Create /TN $taskName /SC DAILY /ST $StartTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to create blind replay task. ExitCode=$LASTEXITCODE" }

Write-Host "Created scheduled blind replay task: $taskName"
Write-Host "Start time: $StartTime"
Write-Host "Command: $tr"
