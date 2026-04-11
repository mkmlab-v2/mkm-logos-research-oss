$ErrorActionPreference = "Stop"

$taskName = "Cursor-Restart-Health-Check"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_cursor_restart_health.ps1"
$baseline = Join-Path $workspaceRoot "scripts\check_cursor_restart_health.ps1"

if (-not (Test-Path $runner)) {
    throw "Runner not found: $runner"
}
if (-not (Test-Path $baseline)) {
    throw "Baseline/check script not found: $baseline"
}

# Initialize baseline once at registration time.
powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File $baseline -InitBaseline | Out-Null

$tr = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC ONLOGON /TR "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File C:\workspace\scripts\run_cursor_restart_health.ps1" /RL LIMITED /F | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Registered task: $taskName"
    Write-Host "Trigger: ONLOGON"
    Write-Host "Command: $tr"
    exit 0
}

# Fallback: user startup shortcut (no Task Scheduler permission required).
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
if (-not (Test-Path $startupDir)) {
    throw "Startup folder not found: $startupDir"
}
$startupCmd = Join-Path $startupDir "cursor_restart_health_check.cmd"
$cmdContent = "@echo off`r`n" +
              "timeout /t 20 /nobreak >nul`r`n" +
              "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"C:\workspace\scripts\run_cursor_restart_health.ps1`"`r`n"
[System.IO.File]::WriteAllText($startupCmd, $cmdContent, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "Task Scheduler registration denied. Fallback applied."
Write-Host "Startup command registered: $startupCmd"
