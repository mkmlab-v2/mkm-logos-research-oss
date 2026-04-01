param(
    [switch]$EnableTaskRegistration
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$registerStrictTask = Join-Path $projectRoot "ops\windows-rehearsal\register_fused_quant_pixel_sop_strict_check_task_clean.ps1"
$registerHealthTask = Join-Path $projectRoot "ops\windows-rehearsal\register_runtime_health_check_task.ps1"
$verifyRuntime = Join-Path $projectRoot "ops\windows-rehearsal\verify_fused_quant_pixel_runtime_health.ps1"
$reportPath = Join-Path $projectRoot "memory\v2\ops\runtime_bootstrap_report_latest.json"

foreach ($p in @($verifyRuntime)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Required script not found: $p"
    }
}
if ($EnableTaskRegistration) {
    foreach ($p in @($registerStrictTask, $registerHealthTask)) {
        if (-not (Test-Path -LiteralPath $p)) {
            throw "Required registration script not found: $p"
        }
    }
}

function Invoke-Step([string]$Name, [string]$ScriptPath) {
    $proc = Start-Process -FilePath "powershell" -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", $ScriptPath) -Wait -PassThru -NoNewWindow
    $code = $proc.ExitCode
    return @{
        name = $Name
        script = $ScriptPath
        exit_code = $code
        ok = ($code -eq 0)
    }
}

function Invoke-VerifyStep([string]$Name, [string]$ScriptPath, [string]$TaskName) {
    $args = @("-ExecutionPolicy", "Bypass", "-File", $ScriptPath, "-TaskName", $TaskName)
    $proc = Start-Process -FilePath "powershell" -ArgumentList $args -Wait -PassThru -NoNewWindow
    $code = $proc.ExitCode
    return @{
        name = $Name
        script = $ScriptPath
        task_name = $TaskName
        exit_code = $code
        ok = ($code -eq 0)
    }
}

$steps = @()
if ($EnableTaskRegistration) {
    $steps += Invoke-Step -Name "register_strict_check_task" -ScriptPath $registerStrictTask
    $steps += Invoke-Step -Name "register_runtime_health_task" -ScriptPath $registerHealthTask
    $steps += Invoke-Step -Name "verify_runtime_health" -ScriptPath $verifyRuntime
} else {
    $steps += @{
        name = "register_runtime_tasks"
        script = "SKIPPED_SAFE_MODE"
        exit_code = 0
        ok = $true
    }
    # Safe mode: verify gateway health and scheduler via bootstrap task itself.
    $steps += Invoke-VerifyStep -Name "verify_runtime_health_safe_mode" -ScriptPath $verifyRuntime -TaskName "Bitcoin-Runtime-Bootstrap-Automation"
}

$allOk = ($steps | Where-Object { -not $_.ok }).Count -eq 0
$result = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    all_ok = $allOk
    steps = $steps
}

$json = $result | ConvertTo-Json -Depth 6
$parent = Split-Path -Parent $reportPath
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
Set-Content -LiteralPath $reportPath -Value $json -Encoding UTF8

Write-Host $json
Write-Host ("Saved runtime bootstrap report: {0}" -f $reportPath)

if (-not $allOk) {
    exit 1
}
exit 0
