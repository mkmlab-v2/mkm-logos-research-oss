#Requires -Version 5.1
<#
.SYNOPSIS
  Evening briefing score + evolution dry-run Telegram (default 20:30).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$At = "20:30",
    [string]$TaskName = "MKM-Commander-Evening-Briefing-Score",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[REMOVED] $TaskName" -ForegroundColor Yellow
    exit 0
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
Set-Location -LiteralPath '__WORKSPACE__'
$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = 'py' }
& $py scripts/fetch_kospi_yfinance_csv.py
if ($LASTEXITCODE -ne 0) { Write-Warning "kospi fetch exit $LASTEXITCODE" }
& $py scripts/fetch_btc_yfinance_csv.py
if ($LASTEXITCODE -ne 0) { Write-Warning "btc fetch exit $LASTEXITCODE" }
& $py scripts/fetch_nasdaq_yfinance_csv.py
if ($LASTEXITCODE -ne 0) { Write-Warning "nasdaq fetch exit $LASTEXITCODE" }
& $py scripts/score_commander_evening_briefing_v1.py --skip-kospi-fetch
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $py scripts/run_commander_briefing_evolution_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($env:MKM_TELEGRAM_EVENING_DIGEST_ENABLED -eq '1') {
  & $py scripts/send_telegram_minimal_ops_digest_v1.py --style evening_review
  exit $LASTEXITCODE
}
Write-Host '[SKIP] evening_review Telegram (MKM_TELEGRAM_EVENING_DIGEST_ENABLED!=1)'
exit 0
'@
$loader = $loader.Replace('__WORKSPACE__', $WorkspaceRoot.Replace("'", "''"))
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"$loader`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Evening score morning briefing + briefing evolution dry-run + Telegram evening_review." -Force | Out-Null
$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] $TaskName at $At Next=$($i.NextRunTime)" -ForegroundColor Green
