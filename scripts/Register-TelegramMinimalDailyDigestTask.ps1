#Requires -Version 5.1
<#
.SYNOPSIS
  Daily premarket Telegram digest (advanced layout) — default 08:28 KST (after 08:18 eval+brief).

.DESCRIPTION
  Builds commander daily fortune, then sends personal-only digest (no KOSPI/BTC/prophecy ops).
  TELEGRAM_* from .env, User env, or DPAPI (Security Agent).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$At = "08:28",
    [string]$TaskName = "MKM-Telegram-Minimal-Daily-Digest",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[REMOVED] $TaskName" -ForegroundColor Yellow
    exit 0
}

$runner = Join-Path $WorkspaceRoot "scripts\send_telegram_minimal_ops_digest_v1.py"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing: $runner"
}

$loader = @'
$dotEnv = Join-Path '__WORKSPACE__' '.env'
if (Test-Path -LiteralPath $dotEnv) {
  Get-Content -LiteralPath $dotEnv -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith('#')) { return }
    $eq = $line.IndexOf('=')
    if ($eq -lt 1) { return }
    $k = $line.Substring(0, $eq).Trim()
    $v = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
    if ($k) { [Environment]::SetEnvironmentVariable($k, $v, 'Process') }
  }
}
foreach ($n in @('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID')) {
  $cur = [Environment]::GetEnvironmentVariable($n, 'Process')
  if ($cur) { continue }
  $u = [Environment]::GetEnvironmentVariable($n, 'User')
  if ($u) { [Environment]::SetEnvironmentVariable($n, $u, 'Process') }
}
$fortunePy = Join-Path '__WORKSPACE__' 'scripts\build_commander_daily_fortune_v1.py'
[Environment]::SetEnvironmentVariable('MKM_TELEGRAM_DIGEST_STYLE', 'advanced', 'Process')
if (Test-Path -LiteralPath $fortunePy) {
  py $fortunePy --skip-regenerate
  if ($LASTEXITCODE -ne 0) { Write-Warning "commander daily fortune exit $LASTEXITCODE; abort send."; exit $LASTEXITCODE }
}
py scripts/build_commander_telegram_advanced_briefing_v1.py --archive
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/send_telegram_minimal_ops_digest_v1.py --style advanced
exit $LASTEXITCODE
'@
$loader = $loader.Replace('__WORKSPACE__', $WorkspaceRoot.Replace("'", "''"))
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"Set-Location -LiteralPath '$($WorkspaceRoot.Replace("'", "''"))'; $loader`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Daily advanced briefing Telegram (08:28, after eval 08:18). fortune + sealed predictions. Style=advanced." -Force | Out-Null

$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] $TaskName at $At Next=$($i.NextRunTime)" -ForegroundColor Green
