param(
    [string]$TaskName = "Bitcoin-Dual-Regime-Gate-Profile-Rotation",
    [int]$IntervalMinutes = 180,
    [int]$StartDelayMinutes = 2,
    [switch]$PersistUserEnv,
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"

$opsRoot = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"
$scriptPath = Join-Path $opsRoot "run_dual_regime_gate_profile_rotation.ps1"
$assertScript = Join-Path $opsRoot "assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $scriptPath -Label "gate profile rotation script"

$argParts = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$scriptPath`""
)
if ($PersistUserEnv) { $argParts += "-PersistUserEnv" }
$tr = "powershell " + ($argParts -join " ")

$st = (Get-Date).AddMinutes($StartDelayMinutes).ToString("HH:mm")

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $TaskName > $null 2>&1
$ErrorActionPreference = $oldEap
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $TaskName /F | Out-Null
}

schtasks /Create /TN $TaskName /SC MINUTE /MO $IntervalMinutes /ST $st /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create task '$TaskName'. ExitCode=$LASTEXITCODE"
}

Write-Host "Created task: $TaskName"
Write-Host "Schedule: every $IntervalMinutes minutes; start=$st"
Write-Host "Command: $tr"

if ($RunNow) {
    if ($PersistUserEnv) {
        & powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File $scriptPath -PersistUserEnv
    } else {
        & powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File $scriptPath
    }
}

